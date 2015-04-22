# -*- coding: utf-8 -*-
"""

"""
from __future__ import division, print_function
import kiwisolver as kiwi
import matplotlib
matplotlib.use('qt4agg')
from matplotlib import pyplot as plt

Variable = kiwi.Variable
sol = kiwi.Solver()
plt.ion()
plt.close('all')


class Box(object):
    """
    Basic rectangle representation using variables
    """

    def __init__(self, name='', solver=sol, lower_left=(0, 0), upper_right=(1, 1), padding=0.1):
        self.name = name
        sn = self.name + '_'
        self.solver = sol
        self.top = Variable(sn + 'top')
        self.bottom = Variable(sn + 'bottom')
        self.left = Variable(sn + 'left')
        self.right = Variable(sn + 'right')

        self.width = Variable(sn + 'width')
        self.height = Variable(sn + 'height')
        self.h_center = Variable(sn + 'h_center')
        self.v_center = Variable(sn + 'v_center')

        self.min_width = Variable(sn + 'min_width')
        self.min_height = Variable(sn + 'min_height')
        self.pref_width = Variable(sn + 'pref_width')
        self.pref_height = Variable(sn + 'pref_height')

        right, top = upper_right
        left, bottom = lower_left
        self.add_constraints()

    def add_constraints(self):
        for i in [self.min_width, self.min_height]:
            sol.addEditVariable(i, 1e9)
            sol.suggestValue(i, 0)
        self.hard_constraints()
        self.soft_constraints()
        sol.updateVariables()

    def hard_constraints(self):
        hc = [self.width == self.right - self.left,
              self.height == self.top - self.bottom,
              self.h_center == (self.left + self.right) * 0.5,
              self.v_center == (self.top + self.bottom) * 0.5,
              self.width >= self.min_width,
              self.height >= self.min_height]
        for c in hc:
            self.solver.addConstraint(c)

    def soft_constraints(self):
        for i in [self.pref_width, self.pref_height]:
            sol.addEditVariable(i, 'strong')
            sol.suggestValue(i, 0)
        c = [(self.pref_width == self.width),
             (self.pref_height == self.height)]
        for i in c:
            sol.addConstraint(i|0.000001)

    def set_geometry(self, left, bottom, right, top, strength=1e9):
        sol = self.solver
        for i in [self.top, self.bottom,
                  self.left, self.right]:
            if not sol.hasEditVariable(i):
                sol.addEditVariable(i, strength)

        sol.suggestValue(self.top, top)
        sol.suggestValue(self.bottom, bottom)
        sol.suggestValue(self.left, left)
        sol.suggestValue(self.right, right)
        sol.updateVariables()

    def get_mpl_rect(self):
        return (round(self.left.value()), round(self.bottom.value()),
                round(self.width.value()), round(self.height.value()))

    def __repr__(self):
        args = (self.name, self.left.value(), self.bottom.value(),
                self.right.value(), self.top.value())
        return 'Rect: %s, (left: %d) (bot: %d)  (right: %d) (top: %d)'%args


class GridLayout(object):

    def __init__(self, rows, cols, width=100, height=100):
        self.rows, self.cols = rows, cols
        self.left_borders = [width / cols * i for i in range(cols)]
        self.right_borders = [width / cols * i for i in range(cols + 1)]
        self.top_borders = [height - height / rows * i for i in range(rows)]
        self.bottom_borders = [height - height / rows * i for i in range(rows+1)]

    def place_rect(self, rect, pos, colspan=1, rowspan=1):
        start_row, start_col = pos
        end_col = start_col + colspan
        end_row = start_row + rowspan

        left, right = self.left_borders[start_col], self.right_borders[end_col]
        top, bottom = self.top_borders[start_row], self.bottom_borders[end_row]

        rect.set_geometry(left, bottom, right, top)


def align(items, attr, strength='weak'):
    """
    Helper function to generate alignment constraints

    Parameters
    ----------
    items: a list of rects to align.
    attr: which attribute to align.

    Returns
    -------
    cons: list of constraints describing the alignment
    """
    cons = []
    for i in items[1:]:
        cons.append((getattr(items[0], attr) == getattr(i, attr)) | strength)
    return cons


def stack(items, direction):
    """
    Helper generating constraints for stacking items in a direction.
    """
    constraints = []

    if direction == 'left':
        first_item, second_item = 'left', 'right'
    elif direction == 'right':
        first_item, second_item = 'right', 'left'
    elif direction == 'top':
        first_item, second_item = 'top', 'bottom'
    elif direction == 'bottom':
        first_item, second_item = 'bottom', 'top'

    for i in range(1, len(items)):
        c = getattr(items[i-1], first_item) <= getattr(items[i], second_item)
        constraints.append(c)
    return constraints


def hstack(items, padding=0):
    constraints = []
    for i in range(1, len(items)):
        constraints.append(items[i-1].right+padding <= items[i].left)
    return constraints


def vstack(items, padding=0):
    constraints = []
    for i in range(1, len(items)):
        constraints.append(items[i-1].bottom-padding >= items[i].top)
    return constraints

fig = plt.figure(dpi=120)


def get_text_size(mpl_txt):
    f = plt.gcf()
    r = f.canvas.get_renderer()
    bbox = mpl_txt.get_window_extent(r)
    return bbox.width, bbox.height


class TextContainer(Box):
    def __init__(self, name):
        super(TextContainer, self).__init__(name)
        self.mpl_text = None

    def set_mpl_text(self, txt):
        self.mpl_text = txt
        txt.set_figure(fig)
        text_ex = get_text_size(txt)
        self.solver.suggestValue(self.min_width, text_ex[0])
        self.solver.suggestValue(self.min_height, text_ex[1])

    def place(self):
        txt = self.mpl_text
        if txt is not None:
            txt.set_position((self.left.value(),
                              self.bottom.value()))
            fig.texts.append(txt)

class RawAxesContainer(Box):
    def __init__(self, name):
        super(RawAxesContainer, self).__init__(name)
        self.adjusted_axes_box = Box()

    def set_axes(self, ax):
        self.axes = ax

    def place(self):
        box = matplotlib.transforms.Bbox.from_bounds(*self.get_mpl_rect())
        invTransFig = fig.transFigure.inverted().transform_bbox
        rect = invTransFig(box)
        if not hasattr(self, 'ax'):
            self.axes = fig.add_axes(rect)
        ax = self.axes
        ax.set_position(rect)
        bbox = ax.get_tightbbox(fig.canvas.get_renderer())
        bbox = invTransFig(bbox)
        dx = rect.xmin-bbox.xmin
        dx2 = rect.xmax-bbox.xmax
        dy = rect.ymin-bbox.ymin
        dy2 = rect.ymax-bbox.ymax
        new_size = (rect.x0 + dx, rect.y0 + dy,
                    rect.width - dx + dx2, rect.height - dy + dy2)
        ax.set_position(new_size)
        self.adjusted_axes_box.set_geometry(*new_size)
        #sol.suggestValue(self.adjusted_axes_box.min_width, new_size[2])

class AxesContainer(Box):
    def __init__(self, name):
        super(AxesContainer, self).__init__(name)
        self.children = []
        self.raw_axes = RawAxesContainer('ax')
        self.top_title = TextContainer('tt')
        self.left_label = TextContainer('ll')
        self.right_label = TextContainer('rl')
        self.top_label = TextContainer('tl')
        self.bottom_label = TextContainer('bl')

        self.children = [self.top_title, self.top_label, self.bottom_label,
                         self.left_label, self.right_label, self.raw_axes]
        self.padding = Variable(name + '_padding')


        self.solver.addEditVariable(self.padding, 'weak')
        self.solver.suggestValue(self.padding, 10)

        constraints = vstack([self.top_title, self.top_label,
                              self.raw_axes, self.bottom_label])
        constraints += hstack([self.left_label, self.raw_axes, self.right_label])
        pad = self.padding
        constraints += [self.left + pad <= self.left_label.left,
                        self.right - pad >= self.right_label.right,
                        self.top - pad >= self.top_title.top,
                        self.bottom + pad <= self.bottom_label.bottom,
                        self.left >= 0,
                        self.bottom >= 0]

        constraints += align([self.top_title, self.top_label,
                              self.raw_axes, self.bottom_label], 'h_center')
        constraints += align([self.left_label, self.raw_axes,
                              self.right_label], 'v_center')

        for c in constraints:
            self.solver.addConstraint(c)
        self.solver.suggestValue(self.raw_axes.pref_width, 1000)
        self.solver.suggestValue(self.raw_axes.pref_height, 1000)
        self.solver.updateVariables()

    def add_label(self, text, where='bottom'):
        d = {'left': self.left_label,
             'right': self.right_label,
             'top': self.top_label,
             'bottom': self.bottom_label,
             'title': self.top_title
             }
        r = d[where]
        if where == 'title':
            fs = plt.rcParams['axes.titlesize']
        else:
            fs = plt.rcParams['xtick.labelsize']

        if where in ('left', 'right'):
            rotation = 'vertical'
        else:
            rotation = 'horizontal'
        txt = plt.Text(0, 0, text=text, transform=None, rotation=rotation,
                       va='bottom', ha='left', fontsize=fs)
        r.set_mpl_text(txt)


    def do_layout(self):
        self.solver.updateVariables()
        for c in self.children:
            c.place()

def find_renderer(fig):
    if hasattr(fig.canvas, "get_renderer"):
        renderer = fig.canvas.get_renderer()
    else:
        import io
        fig.canvas.print_pdf(io.BytesIO())
        renderer = fig._cachedRenderer
    return(renderer)


class FigureLayout(Box):
    def __init__(self):
        self.solver = kiwi.Solver()
        self.children = []
        self.parent = None

    def grid_layout(self, size, hspace=0.1):
        width = self.width.value
        height = self.height.value
        rows, cols = size

        col_splits = [width/cols *i for i in range(cols)]
        row_splits = [height/rows * i for i in range(rows)]

if __name__ == '__main__':
    ac = AxesContainer('ac')
    ac2 = AxesContainer('ac2')
    ac3 = AxesContainer('ac3')
    gl = GridLayout(2, 2, fig.bbox.width, fig.bbox.height)
    gl.place_rect(ac, (0, 0))
    gl.place_rect(ac2, (0, 1), rowspan=2)
    gl.place_rect(ac3, (1, 0))
    sol.addConstraint(ac.top_label.v_center == ac2.top_label.v_center)
    sol.addConstraint(ac.raw_axes.right == ac3.raw_axes.right)

    # ac.add_label('title', 'title')
    ac.add_label('hallo', 'top')
    ac2.add_label('sda', 'top')
    ac2.add_label('title2', 'title')
    ac2.add_label('left', 'left')
    ac3.add_label('Wavenumbers / [cm]', 'right')
    for a in [ac, ac2, ac3]:
        a.do_layout()

    ac.raw_axes.ax.xaxis.set_ticks_position('top')
    ac.do_layout()
    print(ac.top_title, '\n', ac.top_label)

    # print(ac)
    fig.show()
