import cv2, numpy as np, sys
from scipy import ndimage as ndi
from PIL import Image
BG=np.array([244,242,240])
def gmask(rgb):
    a=rgb.astype(int); subj=np.abs(a-BG).max(axis=2)>8
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_s=cv2.GaussianBlur(lab,(0,0),2.0)
    L,A,B=lab_s[...,0],lab_s[...,1],lab_s[...,2]
    white=(lab[...,0]>215)&(np.hypot(lab[...,1]-128,lab[...,2]-128)<9)
    m=subj&(A<138.7)&(B>139.5)&(L>120)&~white
    m=ndi.binary_opening(m,iterations=3); m=ndi.binary_closing(m,iterations=4)
    cl,n=ndi.label(m); sz=ndi.sum(m,cl,range(1,n+1)); m=np.isin(cl,[i+1 for i,v in enumerate(sz) if v>4000])
    m=ndi.binary_fill_holes(m)&~ndi.binary_dilation(white,iterations=2)&subj
    return m,lab
ref=np.asarray(Image.open(sys.argv[1]).convert('RGB')); mr,labr=gmask(ref)
tgt=np.array([np.median(labr[...,i][mr]) for i in range(3)]); print('ref',tgt.round(1),mr.sum())
for f in sys.argv[2:]:
    im=np.asarray(Image.open(f).convert('RGB')); m,lab=gmask(im)
    src=np.array([np.median(lab[...,i][m]) for i in range(3)]); print(f.split('/')[-1],src.round(1),m.sum())
    w=ndi.gaussian_filter(m.astype(np.float32),2.0)[...,None]
    out=lab+(tgt-src)[None,None,:]*w
    Image.fromarray(cv2.cvtColor(np.clip(out,0,255).astype(np.uint8),cv2.COLOR_LAB2RGB)).save(f.replace('.webp','-toned.png'))
    Image.fromarray((m*255).astype(np.uint8)).save(f.replace('.webp','-mask.png'))
Image.fromarray((mr*255).astype(np.uint8)).save(sys.argv[1].replace('.webp','-mask.png'))
