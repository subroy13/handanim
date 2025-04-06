import cairo

class Text:
    def __init__(self, content, position=(0, 0), font_size=32, color=(0, 0, 0), font_family="Cursive", style="handwritten"):
        self.content = content
        self.position = position
        self.font_size = font_size
        self.color = color  # RGB tuple
        self.font_family = font_family
        self.style = style  # Can be extended in future for different styles

    def draw(self, ctx: cairo.Context):
        ctx.save()
        ctx.select_font_face(self.font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(self.font_size)
        ctx.set_source_rgb(*self.color)

        x, y = self.position
        ctx.move_to(x, y)
        ctx.show_text(self.content)
        ctx.stroke()
        ctx.restore()
