import numpy as np, json
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
P=''
img=Image.open(P+'dl/map74_hi-1.png').convert('RGB')
im=np.asarray(img).astype(int); H,W,_=im.shape
cut=int(H*0.6); im=im[:cut]
r,g,b=im[...,0],im[...,1],im[...,2]
red=(r>190)&(g<110)&(b<110)
# include dark station glyphs / lines inside circles: fill holes after closing
red=ndi.binary_closing(red,structure=np.ones((3,3)),iterations=3)
red=ndi.binary_fill_holes(red)
for rad in (30,32,33,34):
    yy,xx=np.mgrid[-rad:rad+1,-rad:rad+1]; disk=(xx**2+yy**2)<=rad**2
    er=ndi.binary_erosion(red,structure=disk)
    lab,n=ndi.label(er)
    print(rad,n)
rad=32
yy,xx=np.mgrid[-rad:rad+1,-rad:rad+1]; disk=(xx**2+yy**2)<=rad**2
er=ndi.binary_erosion(red,structure=disk)
lab,n=ndi.label(er)
cs=ndi.center_of_mass(er,lab,range(1,n+1))
sizes=ndi.sum(er,lab,range(1,n+1))
pts=[(round(x),round(y),int(s)) for (y,x),s in zip(cs,sizes)]
json.dump(pts,open('work/circles2.json','w'))
d=ImageDraw.Draw(img)
for i,(x,y,s) in enumerate(pts):
    d.ellipse((x-7,y-7,x+7,y+7),fill=(0,0,255))
    d.text((x+10,y-34),str(i),fill=(0,0,0))
img.crop((0,0,W,cut)).save('work/circles2_full.png')
img.crop((900,1050,2496,1600)).save('work/circles2_core.png')
print(sorted(pts,key=lambda p:p[2])[:8])
