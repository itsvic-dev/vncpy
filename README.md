# vncpy

a tiny implementation of RFC 6143 (RFB) version 3.8, which just sends a static image to the client.

features:

- ☑️ basic RFB 3.8
- ☑️ known to work with TigerVNC, novnc and wlvncc
- ☑️ very tiny, easily understandable and extensible
- ❌ does not support 3.3 and 3.7 clients
- ❌ does not support partial framebuffer updates
- ❌ does not support pixel formats other than the default

## supported encoding types

| s32 | type               |
| --- | ------------------ |
| 0   | raw                |
| 6   | zlib (not popular) |
