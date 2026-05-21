import jpeg.io


class Segment:
    def write(self, writer: jpeg.io.Writer) -> None:
        raise NotImplementedError
