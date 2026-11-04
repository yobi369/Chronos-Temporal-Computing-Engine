# Statistical benchmark protocol

The benchmark runner must use matched workload parameters, alternate execution order, preserve raw paired samples, and report a paired bootstrap interval for the median latency difference. Reproductions should be run independently on at least two machines and compare environment manifests before pooling results. The built-in script is an engineering protocol, not evidence of universal performance. Bootstrap intervals quantify resampling uncertainty under the observed sample; they do not remove systematic machine, runtime or workload bias.
