import pyjpeg


def test_arithmetic_scan():
    writer = pyjpeg.BufferedWriter()
    scan_writer = pyjpeg.arithmetic_scan.Writer(writer)
    dc_non_zero = pyjpeg.arithmetic.State()
    dc_sign = pyjpeg.arithmetic.State()
    dc_sp = pyjpeg.arithmetic.State()
    dc_sn = pyjpeg.arithmetic.State()
    dc_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    dc_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_non_zero = [pyjpeg.arithmetic.State() for _ in range(63)]
    ac_sn_sp_x1 = pyjpeg.arithmetic.State()
    ac_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_eob = pyjpeg.arithmetic.State()
    scan_writer.write_dc(
        123, dc_non_zero, dc_sign, dc_sp, dc_sn, dc_xstates, dc_mstates
    )
    scan_writer.write_zeros(3, ac_non_zero)
    scan_writer.write_ac(55, ac_sn_sp_x1, ac_xstates, ac_mstates)
    scan_writer.write_eob(True, ac_eob)
    scan_writer.flush()

    dc_non_zero = pyjpeg.arithmetic.State()
    dc_sign = pyjpeg.arithmetic.State()
    dc_sp = pyjpeg.arithmetic.State()
    dc_sn = pyjpeg.arithmetic.State()
    dc_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    dc_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_non_zero = [pyjpeg.arithmetic.State() for _ in range(63)]
    ac_sn_sp_x1 = pyjpeg.arithmetic.State()
    ac_xstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_mstates = [pyjpeg.arithmetic.State() for _ in range(16)]
    ac_eob = pyjpeg.arithmetic.State()
    reader = pyjpeg.BufferedReader(writer.data)
    scan_reader = pyjpeg.arithmetic_scan.Reader(reader)
    dc = scan_reader.read_dc(dc_non_zero, dc_sign, dc_sp, dc_sn, dc_xstates, dc_mstates)
    assert dc == 123
    run_length = scan_reader.read_zeros(ac_non_zero)
    assert run_length == 3
    ac = scan_reader.read_ac(ac_sn_sp_x1, ac_xstates, ac_mstates)
    assert ac == 55
    is_eob = scan_reader.read_eob(ac_eob)
    assert is_eob
