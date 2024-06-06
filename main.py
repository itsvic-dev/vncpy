import socketserver
import struct
import sys
from PIL import Image

img = Image.open(sys.argv[1])

print("Loading and preprocessing image data...")
redPixels = img.getdata(0)
greenPixels = img.getdata(1)
bluePixels = img.getdata(2)
pixels = [
    (redPixels[i] << 16 | greenPixels[i] << 8 | bluePixels[i])
    for i in range(len(redPixels))
]
pixelsBytes = struct.pack("<" + "I" * len(pixels), *pixels)


# implementation of RFB 3.8 (does not fall back to 3.7 or 3.3 currently)
class RFBHandler(socketserver.BaseRequestHandler):
    def pack_string(self, string: str):
        string_bytes = string.encode()
        return self.pack_u32(len(string_bytes)) + string_bytes

    def send_string(self, string: str):
        self.request.sendall(pack_string(string))

    @staticmethod
    def pack_u32(num):
        return struct.pack(">I", num)

    @staticmethod
    def pack_u16(num):
        return struct.pack(">H", num)

    def recv_u16(self):
        return struct.unpack(">H", self.request.recv(2))[0]

    def recv_s32(self):
        return struct.unpack(">i", self.request.recv(4))[0]

    def recv_u32(self):
        return struct.unpack(">I", self.request.recv(4))[0]

    def handle(self):
        print(f"hello {self.client_address}")
        self.pixelFormatStruct = (
            bytes(
                [
                    32,  # bits per pixel
                    24,  # depth
                    0,  # big endian flag
                    1,  # true color flag
                ]
            )
            + self.pack_u16(255)  # red-max
            + self.pack_u16(255)  # green-max
            + self.pack_u16(255)  # blue-max
            + bytes([16, 8, 0])  # red-shift, green-shift, blue-shift
            + b"\0\0\0"  # 3 padding bytes
        )

        # ProtocolVersion from server
        self.request.sendall(b"RFB 003.008\n")

        # ProtocolVersion from client
        clientProtocol = self.request.recv(12)
        if clientProtocol != b"RFB 003.008\n":
            # terminate the connection
            self.request.sendall(b"\0")
            self.send_string("sorry but i don't 3.7 or lower")
            return

        # SecurityHandshake from server
        self.request.sendall(b"\1\1")

        # SecurityHandshake from client
        clientSecurity = self.request.recv(1)[0]

        # SecurityResult
        if clientSecurity != 1:
            # failed
            self.request.sendall(self.pack_u32(1))
            self.send_string("i only support None security")
            return
        else:
            # success
            self.request.sendall(self.pack_u32(0))

        # ClientInit
        sharedFlag = self.request.recv(1)[0]

        # ServerInit
        self.request.sendall(
            self.pack_u16(img.width)
            + self.pack_u16(img.height)
            + self.pixelFormatStruct
            + self.pack_string("vncpy")
        )

        while True:
            # main message loop
            try:
                message_type = self.request.recv(1)[0]
            except (IndexError, ConnectionResetError):
                # client terminated
                print(f"bye {self.client_address}")
                return

            if message_type == 0:
                self.setPixelFormat()
            if message_type == 2:
                self.setEncodings()
            if message_type == 3:
                self.framebufferUpdateRequest()
            if message_type == 4:
                # KeyEvent
                self.request.recv(1 + 2 + 4)  # read and ignore
            if message_type == 5:
                # PointerEvent
                self.request.recv(1 + 2 + 2)  # read and ignore
            if message_type == 6:
                # ClientCutText
                # we have to read the length of the string to ignore it, ughh
                self.request.recv(3)  # padding
                length = self.recv_u32()
                self.request.recv(length)

    def sendEntireFramebuffer(self):
        messageHeader = struct.pack(
            ">BBH",
            0,  # message-type
            0,  # padding
            1,  # number-of-rectangles
        )

        encodingType = 0  # raw
        rectangle = (
            struct.pack(">HHHHi", 0, 0, img.width, img.height, encodingType)
            + pixelsBytes
        )

        self.request.sendall(messageHeader + rectangle)

    def setPixelFormat(self):
        self.request.recv(3)  # padding

        pixelFormat = self.request.recv(16)
        if pixelFormat != self.pixelFormatStruct:
            print(
                f"client requested {pixelFormat=} but we provide {self.pixelFormatStruct}. this will break things!!!"
            )

    def setEncodings(self):
        self.request.recv(1)  # padding

        requestedEncodings = []
        numberOfEncodings = self.recv_u16()
        for _ in range(numberOfEncodings):
            requestedEncodings.append(self.recv_s32())

    def framebufferUpdateRequest(self):
        (incremental, xPos, yPos, width, height) = struct.unpack(
            ">?HHHH", self.request.recv(1 + 4 * 2)
        )
        # too lazy to implement partial updates lol
        self.sendEntireFramebuffer()


if __name__ == "__main__":
    addr = ("0.0.0.0", 5900)

    print(f"Serving RFB on {addr}")

    with socketserver.ForkingTCPServer(addr, RFBHandler) as server:
        server.serve_forever()
