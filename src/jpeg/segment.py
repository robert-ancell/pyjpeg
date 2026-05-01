import jpeg.io


class Segment:
    def write(self, writer: jpeg.io.Writer):
        raise NotImplementedError

    def read(reader: jpeg.io.Reader):
        raise NotImplementedError
