# 모델 피부 색조만 기준 사진의 피부 색조에 맞춘다. 제품(원단)·배경·머리카락·형태는 건드리지 않는다.
import cv2, numpy as np, sys, os
from scipy import ndimage as ndi
from PIL import Image
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
def skin(rgb):
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB).astype(np.float32)
    s=cv2.GaussianBlur(lab,(0,0),2.5); L,A,B=s[...,0],s[...,1],s[...,2]
    body=(B>138)&(L>125)&(A>133)                       # 피부+원단(배경·머리카락 제외)
    sk=body&(A>143.3); ga=body&(A<140.6)               # 확실한 피부 / 확실한 원단
    X=s[body]; y=np.full(body.sum(),-1); y[sk[body]]=1; y[ga[body]]=0
    clf=LDA().fit(X[y>=0],y[y>=0]); pr=clf.predict_proba(X)[:,1]
    P=np.zeros(L.shape,np.float32); P[body]=pr
    m=P>0.5
    m=ndi.binary_opening(m,iterations=3); m=ndi.binary_closing(m,iterations=3)
    cl,n=ndi.label(m); sz=ndi.sum(m,cl,range(1,n+1)); m=np.isin(cl,[i+1 for i,v in enumerate(sz) if v>1500])
    return m,lab
def med(lab,m): return np.array([np.median(lab[...,i][m]) for i in range(3)])
if __name__=='__main__':
    out_dir=sys.argv[1]; ref=np.asarray(Image.open(sys.argv[2]).convert('RGB')); mr,lr=skin(ref); tgt=med(lr,mr); print('ref skin',tgt.round(1),mr.sum())
    Image.fromarray((mr*255).astype(np.uint8)).save(out_dir+'/ref-mask.png')
    for f in sys.argv[3:]:
        im=np.asarray(Image.open(f).convert('RGB')); m,lab=skin(im); src=med(lab,m); n=os.path.basename(f).replace('.webp','')
        print(n,'skin',src.round(1),m.sum(),'delta',(tgt-src).round(1))
        w=ndi.gaussian_filter(m.astype(np.float32),2.5)[...,None]
        res=lab+(tgt-src)[None,None,:]*w
        Image.fromarray(cv2.cvtColor(np.clip(res,0,255).astype(np.uint8),cv2.COLOR_LAB2RGB)).save(f'{out_dir}/{n}-skin.png')
        Image.fromarray((m*255).astype(np.uint8)).save(f'{out_dir}/{n}-mask.png')
