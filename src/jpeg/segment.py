import jpeg.io


class Segment:
    def write(self, writer: jpeg.io.Writer):
        raise NotImplementedError

    @classmethod
    def read(cls, reader: jpeg.io.Reader):
        raise NotImplementedError
