import pyjpeg.io


class Segment:
    def write(self, writer: pyjpeg.io.Writer) -> None:
        raise NotImplementedError
