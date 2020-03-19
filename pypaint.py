import os
import random

import pygame as pg


class App:

    def __init__(self):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pg.init()
        self.w, self.h = 640, 480
        self.screen = pg.display.set_mode((self.w, self.h))
        self.screen.fill(pg.Color('white'))
        self.clock = pg.time.Clock()
        self.drawcolor = (0, 0, 0)
    
    def mainloop(self):
    
        def inpt():
            word=""
            pg.display.flip()
            done = True
            while done:
                for event in pg.event.get():
                    if event.type==pg.QUIT:
                        pg.quit()
                        quit()
                    if event.type == pg.KEYDOWN:
                        word+=str(chr(event.key))
                        
                        if event.key == pg.K_RETURN:
                            done=False
                            res = tuple(map(int, word.split(','))) 
            return res
        
        
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return
                    
                if event.type == pg.KEYDOWN:    
                    if event.key == pg.K_c:
                        self.drawcolor = (inpt())
                        
                    if event.key == pg.K_s:
                        pg.image.save(self.screen, "image.bmp")
                        
                    if event.key == pg.K_l:
                        image = pg.image.load(os.path.join("image.bmp"))
                        self.screen.blit(image,(0,0))
                        
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                    
                elif event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == 3:  # Color picker (middle mouse button).
                        self.drawcolor = self.screen.get_at(pos)
                        # Pick a random color.
                        # self.drawcolor = [random.randrange(256) for _ in range(3)]
                elif event.type == pg.MOUSEMOTION:
                    pos, rel = event.pos, event.rel
                    if event.buttons[0]:  # If the left mouse button is down.
                        # Draw a line from the pos to the previous pos.
                        pg.draw.line(self.screen, self.drawcolor, pos, (pos[0]-rel[0], pos[1]-rel[1]), 5)
                    

            pg.display.flip()
            self.clock.tick(30)


if __name__ == '__main__':
    app = App()
    app.mainloop()
    pg.quit()