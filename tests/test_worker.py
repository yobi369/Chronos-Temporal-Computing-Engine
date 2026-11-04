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


def test_worker_handler_failure_leaves_inbox_for_retry(tmp_path):
    store=DurableMessageStore(tmp_path/"receiver.db")
    message={"message_id":"retry-handler","source":"a","target":"b","kind":"task","payload":{"x":1}}
    assert store.accept(message) is True
    server=WorkerServer("b",SECRET,store)
    calls=[]
    def flaky(message):
        calls.append(message["message_id"])
        if len(calls)==1:
            raise RuntimeError("temporary handler failure")
    server.register_handler("task",flaky)
    with pytest.raises(RuntimeError,match="temporary"):
        server.process_pending()
    assert len(store.inbox_pending())==1
    assert server.process_pending()==1
    assert len(store.inbox_pending())==0
    assert calls==["retry-handler","retry-handler"]


def test_worker_recovers_after_network_partition_and_delivers_durable_message(tmp_path):
    async def scenario():
        sender=DurableMessageStore(tmp_path/"sender.db")
        receiver=DurableMessageStore(tmp_path/"receiver.db")
        client=WorkerClient("source",SECRET,sender)
        client.publish("target","task",{"value":"recovered"},message_id="partition-message")
        delivered,failed=await client.deliver_pending("127.0.0.1",1,now=100,timeout=0.05)
        assert (delivered,failed)==(0,1)
        assert sender.pending_count()==1
        server=WorkerServer("target",SECRET,receiver)
        handled=[]
        server.register_handler("task",lambda message: handled.append(message["payload"]["value"]))
        host,port=await server.start()
        try:
            delivered,failed=await client.deliver_pending(host,port,now=101)
            assert (delivered,failed)==(1,0)
            assert sender.pending_count()==0
            assert server.process_pending()==1
            assert handled==["recovered"]
        finally:
            await server.close()
    asyncio.run(scenario())


def test_worker_client_background_delivery_loop_drains_durable_outbox(tmp_path):
    async def scenario():
        sender=DurableMessageStore(tmp_path/"sender.db")
        receiver=DurableMessageStore(tmp_path/"receiver.db")
        server=WorkerServer("target",SECRET,receiver)
        host,port=await server.start()
        client=WorkerClient("source",SECRET,sender)
        client.publish("target","task",{"n":7},message_id="background-loop")
        stop=asyncio.Event()
        task=asyncio.create_task(client.run_forever(host,port,stop,poll_interval=0.01))
        try:
            for _ in range(1000):
                if receiver.inbox_pending() and sender.pending_count()==0:
                    break
                await asyncio.sleep(0.01)
            assert receiver.inbox_pending()
            assert sender.pending_count()==0
        finally:
            stop.set()
            await asyncio.wait_for(task,timeout=1)
            await server.close()
    asyncio.run(scenario())
