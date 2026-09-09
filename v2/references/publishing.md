# V2 Publishing Reference

V2 publishing uses the v1 shared publishing contract and adds behavior-spec freshness checks.

Before a push or draft PR/MR, v2 must verify:

- the user's request explicitly allows the push or PR/MR
- the selected profile's provider guard passes
- committed HEAD is the intended source revision
- the selected behavior spec digest matches the digest used by verification
- required scenario results are passed or explicitly waived by policy
- generated tracked specs or tests created after commit are committed or marked disposable by config

Missing optional media remains governed by the selected profile's evidence policy. Missing required behavior coverage is a separate gate and must not be converted into a media warning.
