# 모델 피부 색조만 기준 사진의 피부 색조에 맞춘다. 제품(원단)·배경·머리카락·형태는 건드리지 않는다.
import cv2, numpy as np, sys
from scipy import ndimage as ndi
from PIL import Image
def skin(rgb,thr=141.8):
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB).astype(np.float32)
    s=cv2.GaussianBlur(lab,(0,0),2.5)
    L,A,B=s[...,0],s[...,1],s[...,2]
    m=(A>thr)&(B>136)&(L>125)
    m=ndi.binary_opening(m,iterations=2); m=ndi.binary_closing(m,iterations=3)
    cl,n=ndi.label(m); sz=ndi.sum(m,cl,range(1,n+1)); m=np.isin(cl,[i+1 for i,v in enumerate(sz) if v>600])
    return m,lab
def med(lab,m): return np.array([np.median(lab[...,i][m]) for i in range(3)])
if __name__=='__main__':
    ref=np.asarray(Image.open(sys.argv[1]).convert('RGB')); mr,lr=skin(ref); tgt=med(lr,mr); print('ref skin',tgt.round(1),mr.sum())
    for f in sys.argv[2:]:
        im=np.asarray(Image.open(f).convert('RGB')); m,lab=skin(im); src=med(lab,m)
        print(f.split('/')[-1],'skin',src.round(1),m.sum(),'delta',(tgt-src).round(1))
        w=ndi.gaussian_filter(m.astype(np.float32),2.5)[...,None]
        out=lab+(tgt-src)[None,None,:]*w
        o=f.replace('.webp','-skin.png').replace('/img/','/')
        Image.fromarray(cv2.cvtColor(np.clip(out,0,255).astype(np.uint8),cv2.COLOR_LAB2RGB)).save(sys.argv[0].rsplit('/',1)[0]+'/'+f.split('/')[-1].replace('.webp','-skin.png'))
        Image.fromarray((m*255).astype(np.uint8)).save(sys.argv[0].rsplit('/',1)[0]+'/'+f.split('/')[-1].replace('.webp','-mask.png'))
    Image.fromarray((mr*255).astype(np.uint8)).save(sys.argv[0].rsplit('/',1)[0]+'/ref-mask.png')
