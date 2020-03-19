import os
import random
import sys
import pygame as pg


class App:

    def __init__(self,imgWidth,imgHeight):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pg.init()
        self.screen = pg.display.set_mode((imgWidth, imgHeight))
        self.screen.fill(pg.Color(0,0,0))
        self.clock = pg.time.Clock()
        self.drawcolor = (255,255,255)
    
    def mainloop(self,imgName):
    
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
                        pg.image.save(self.screen, imgName)
                        
                    if event.key == pg.K_l:
                        image = pg.image.load(os.path.join(imgName))
                        self.screen.blit(image,(0,0))
                        
                    if event.key == pg.K_ESCAPE:
                        pg.quit()
                    
                elif event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == 3:  
                        self.drawcolor = self.screen.get_at(pos)
                       
                elif event.type == pg.MOUSEMOTION:
                    pos, rel = event.pos, event.rel
                    if event.buttons[0]:  
                        pg.draw.line(self.screen, self.drawcolor, pos, (pos[0]-rel[0], pos[1]-rel[1]), 5)
                    

            pg.display.flip()
            self.clock.tick(30)


if __name__ == '__main__':
    app = App(640,480)
    app.mainloop("image.bmp")
    pg.quit()