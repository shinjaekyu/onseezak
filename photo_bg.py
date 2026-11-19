# 모델 사진의 배경만 공홈 스튜디오 색(#F4F2F0)으로 바꾸고 3:4(900x1200)로 맞춘다. 인물·제품 픽셀은 건드리지 않는다.
from PIL import Image
import numpy as np, sys
from scipy import ndimage as ndi
BG=np.array([244,242,240],float)
def run(src,dst):
    im=Image.open(src).convert('RGB'); a=np.asarray(im).astype(float); h,w,_=a.shape
    edge=np.concatenate([a[:,:12],a[:,-12:]],axis=1); rowbg=np.median(edge,axis=1)
    rowbg=ndi.uniform_filter1d(rowbg,size=41,axis=0,mode='nearest')
    d=np.abs(a-rowbg[:,None,:]).max(axis=2); d=ndi.gaussian_filter(d,0.7)
    soft=np.clip((d-7)/(20-7),0,1); bgish=soft<0.5
    lab,n=ndi.label(bgish)
    border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
    keep=set(border); sizes=ndi.sum(bgish,lab,range(1,n+1))
    for i in range(1,n+1):
        if i in border or sizes[i-1]<60: continue
        m=lab==i
        if a[m].std(axis=0).mean()<3.5 and d[m].mean()<6.6: keep.add(i)   # 팔과 몸 사이처럼 갇힌 배경
    conn=ndi.binary_dilation(np.isin(lab,list(keep)),iterations=2)
    alpha=np.where(conn,soft,1.0)
    # 인물에서 떨어진 배경의 얼룩(원본 배경의 옅은 띠)은 완전히 지운다. 발밑 그림자는 남긴다.
    core=soft>0.8; cl,cn=ndi.label(core); cs=ndi.sum(core,cl,range(1,cn+1))
    core=np.isin(cl,[i+1 for i,v in enumerate(cs) if v>2000])
    dist=ndi.distance_transform_edt(~core)
    bottom=np.where(core.any(axis=1))[0].max()
    yy=np.arange(h)[:,None]
    alpha=np.where(conn&(dist>10)&(yy<bottom-0.12*h),0.0,alpha)
    alpha=ndi.gaussian_filter(alpha,0.6)
    out=a*alpha[...,None]+BG*(1-alpha[...,None]); o=Image.fromarray(out.clip(0,255).astype('uint8'))
    if w/h>0.75: nw,nh=900,round(h*900/w)
    else: nh,nw=1200,round(w*1200/h)
    o=o.resize((nw,nh),Image.LANCZOS); cv=Image.new('RGB',(900,1200),(244,242,240)); cv.paste(o,((900-nw)//2,(1200-nh)//2))
    cv.save(dst,quality=88,method=6)
if __name__=='__main__': run(sys.argv[1],sys.argv[2])
