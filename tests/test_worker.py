# ruff: noqa: E501, E701, E702
import asyncio
import pytest
from chronos.worker import (DurableMessageStore,WorkerClient,WorkerServer,sign_message,verify_message,WorkerProtocolError)

SECRET=b"chronos-test-secret-material-at-least-32-bytes"

def test_hmac_message_authentication_rejects_tampering():
    doc=sign_message({"message_id":"m1","source":"a","target":"b","kind":"event","payload":{"n":1}},SECRET)
    assert verify_message(doc,SECRET)["payload"]["n"]==1
    doc["message"]["payload"]["n"]=2
    with pytest.raises(WorkerProtocolError,match="authentication"):
        verify_message(doc,SECRET)

def test_durable_worker_delivery_and_inbox_deduplication(tmp_path):
    async def scenario():
        sender_store=DurableMessageStore(tmp_path/"sender.db")
        receiver_store=DurableMessageStore(tmp_path/"receiver.db")
        server=WorkerServer("worker-b",SECRET,receiver_store)
        processed=[]
        server.register_handler("event",lambda message: processed.append(message["payload"]["value"]))
        host,port=await server.start()
        client=WorkerClient("worker-a",SECRET,sender_store)
        message_id=client.publish("worker-b","event",{"value":9},message_id="stable-id")
        assert sender_store.pending_count()==1
        delivered,failed=await client.deliver_pending(host,port)
        assert (delivered,failed)==(1,0)
        assert sender_store.pending_count()==0
        message={"message_id":message_id,"source":"worker-a","target":"worker-b","kind":"event","payload":{"value":9}}
        assert receiver_store.accept(message) is False
        assert server.process_pending()==1
        assert processed==[9]
        assert server.process_pending()==0
        await server.close()
    asyncio.run(scenario())

def test_durable_outbox_retry_backoff_survives_store_reopen(tmp_path):
    async def scenario():
        store=DurableMessageStore(tmp_path/"sender.db")
        client=WorkerClient("a",SECRET,store)
        client.publish("b","event",{"x":1},message_id="retry-me")
        delivered,failed=await client.deliver_pending("127.0.0.1",1,now=100,timeout=0.05)
        assert (delivered,failed)==(0,1)
        reopened=DurableMessageStore(tmp_path/"sender.db")
        assert reopened.due(now=100)==()
        assert len(reopened.due(now=200))==1
    asyncio.run(scenario())
