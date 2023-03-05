class Color:
    GREEN = [24, 20, 25, 26, 22, 21]
    CYAN = [40, 36, 37, 38, 41, 42]
    AQUA = [32, 28, 33, 34, 29, 30]
    BLUE_PURPLE = [48, 49, 50, 44, 45, 46]
    PINK = [56, 52, 53, 54, 57, 58]
    YELLOW_GREEN = [12, 13, 14, 16, 17, 18]
    RED_ORANGE = [8, 9, 10, 4, 5, 6]

    class Intensity:
        _0 = 0
        _1 = 1
        _2 = 2
        _3 = 3
        _4 = 4
        _5 = 5

    def __init__(self, id, value):
        self.id = id
        self.value = value

    @staticmethod
    def get(color: list[int], intensity: int):
        return color[intensity]
