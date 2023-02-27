LAYOUT = """
    104 | 105 | 106 | 107 | 108 | 109 | 110 | 111 || 112
    ====================================================
     81 |  82 |  83 |  84 |  85 |  86 |  87 |  88 ||  89
     71 |  72 |  73 |  74 |  75 |  76 |  77 |  78 ||  79
     61 |  62 |  63 |  64 |  65 |  66 |  67 |  68 ||  69
     51 |  52 |  53 |  54 |  55 |  56 |  57 |  58 ||  59
     41 |  42 |  43 |  44 |  45 |  46 |  47 |  48 ||  49
     31 |  32 |  33 |  34 |  35 |  36 |  37 |  38 ||  39
     21 |  22 |  23 |  24 |  25 |  26 |  27 |  28 ||  29
     11 |  12 |  13 |  14 |  15 |  16 |  17 |  18 ||  19
"""
TEMPLATE = """
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    ===========================================
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
    {} | {} | {} | {} | {} | {} | {} | {} || {}
"""

def transpose(matrix):
    return [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]


def flatten(matrix):
    return [item for sublist in matrix for item in sublist]


class LaunchpadLayout:
    def __init__(self, layout_description=LAYOUT) -> None:
        lines = layout_description.splitlines()
        lines = [line.strip() for line in lines if line if line.strip()]
        lines = [line.replace('||', '|') for line in lines]
        lines = [line for line in lines if not '=' in line]
        str_rows = [line.split('|') for line in lines]
        self.rows = [[int(cell.strip()) for cell in row] for row in str_rows]
        first_row = self.rows.pop(0)
        up, down, left, right, _0, _1, _2, _3, _99 = first_row
        self.up = up
        self.down = down
        self.left = left
        self.right = right
        self.page0 = _0
        self.page1 = _1
        self.page2 = _2
        self.page3 = _3
        self._99 = _99
        self.columns = transpose(self.rows)
        last_column = self.columns.pop()
        self.rows = transpose(self.columns)
        _0, _1, _2, _3, _4, _5, _6, _7 = last_column
        self.channel0 = _0
        self.channel1 = _1
        self.channel2 = _2
        self.channel3 = _3
        self.channel4 = _4
        self.channel5 = _5
        self.channel6 = _6
        self.channel7 = _7
        self.top_row = [self.up,
                        self.down,
                        self.left,
                        self.right,
                        self.page0,
                        self.page1,
                        self.page2,
                        self.page3]
        self.last_column = [self._99,
                            self.channel0,
                            self.channel1,
                            self.channel2,
                            self.channel3,
                            self.channel4,
                            self.channel5,
                            self.channel6,
                            self.channel7]
    
    def is_menu_pad(self, pad):
        return pad in self.top_row

    def is_channel_pad(self, pad):
        return pad in self.last_column

    def pad_to_arp_index(self, pad):
        for column in self.columns:
            if pad in column:
                reversed_column = column[:]
                reversed_column.reverse()
                return reversed_column.index(pad)
        return 0

    def __str__(self):
        rows = [self.top_row] + self.rows
        columns = transpose(rows)
        columns = columns + [self.last_column]
        rows = transpose(columns)
        return TEMPLATE.format(*flatten(rows))
