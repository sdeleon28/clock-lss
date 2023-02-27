PAGES = 4
STEPS_PER_PAGE = 8

def get_page_for_tick(tick):
    return (tick // STEPS_PER_PAGE) % PAGES

def get_page_position_for_tick(tick):
    return tick % STEPS_PER_PAGE

def test():
    # get_page_for_tick
    assert get_page_for_tick(0) == 0
    assert get_page_for_tick(1) == 0
    assert get_page_for_tick(8) == 1
    assert get_page_for_tick(9) == 1
    assert get_page_for_tick(16) == 2
    assert get_page_for_tick(17) == 2
    assert get_page_for_tick(19) == 2
    assert get_page_for_tick(24) == 3
    assert get_page_for_tick(25) == 3
    assert get_page_for_tick(32) == 0
    assert get_page_for_tick(33) == 0
    assert get_page_for_tick(40) == 1
    assert get_page_for_tick(41) == 1

    # get_page_position_for_tick
    assert get_page_position_for_tick(0) == 0
    assert get_page_position_for_tick(1) == 1
    assert get_page_position_for_tick(8) == 0
    assert get_page_position_for_tick(9) == 1
    assert get_page_position_for_tick(16) == 0
    assert get_page_position_for_tick(17) == 1
    assert get_page_position_for_tick(19) == 3
    assert get_page_position_for_tick(24) == 0
    assert get_page_position_for_tick(25) == 1
    assert get_page_position_for_tick(32) == 0
    assert get_page_position_for_tick(33) == 1
    assert get_page_position_for_tick(40) == 0
    assert get_page_position_for_tick(41) == 1

if __name__ == '__main__':
    test()
