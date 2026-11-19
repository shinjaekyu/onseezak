# 모델 컷 정리: 피부 색조(B안) → 선명도·해상도 개선(EDSR 2배) → 미니멀 스튜디오 배경(#F4F2F0) → 1350x1800 / 900x1200 / 360x480 저장
# 제품(원단) 색·모양, 모델 체형은 건드리지 않는다.
import cv2, numpy as np, sys, time
from scipy import ndimage as ndi
from PIL import Image, ImageFilter
from skin2 import skin, med
from skin import skin as skin_simple
BG=np.array([244,242,240],np.float32)
I='/home/claude/onseezak/assets/img/'
def bg_alpha(a):
    h,w,_=a.shape
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
        if a[m].std(axis=0).mean()<3.5 and d[m].mean()<6.6: keep.add(i)
    conn=ndi.binary_dilation(np.isin(lab,list(keep)),iterations=2)
    alpha=np.where(conn,soft,1.0)
    core=soft>0.8; cl,cn=ndi.label(core); cs=ndi.sum(core,cl,range(1,cn+1))
    core=np.isin(cl,[i+1 for i,v in enumerate(cs) if v>2000])
    dist=ndi.distance_transform_edt(~core); bottom=np.where(core.any(axis=1))[0].max(); yy=np.arange(h)[:,None]
    alpha=np.where(conn&(dist>10),0.0,alpha)
    labc=cv2.cvtColor(a.clip(0,255).astype(np.uint8),cv2.COLOR_RGB2LAB).astype(np.float32)
    labc=cv2.GaussianBlur(labc,(0,0),1.5); chroma=np.hypot(labc[...,1]-128,labc[...,2]-128)
    shadow=(chroma<11)&(labc[...,0]>140)&(yy>bottom-0.12*h)          # 발밑의 회색 그림자(피부·원단은 채도가 높아 제외됨)
    shadow=ndi.binary_dilation(ndi.binary_opening(shadow,iterations=1),iterations=1)
    alpha=np.where(shadow,0.0,alpha)
    lum=a.mean(axis=2); rb=rowbg.mean(axis=1)[:,None]
    ratio=np.where((conn|shadow)&(alpha<0.5),lum/rb,1.0)
    ratio=np.where(yy>bottom-0.10*h,ratio,1.0)                     # 발밑 그림자만
    ratio=ndi.gaussian_filter(np.clip(ratio,0.80,1.0),4.0)
    ratio=np.where(ratio>0.992,1.0,ratio)
    return ndi.gaussian_filter(alpha,0.6).astype(np.float32), ratio.astype(np.float32)
sr=cv2.dnn_superres.DnnSuperResImpl_create(); sr.readModel('model/EDSR_x2.pb'); sr.setModel('edsr',2)
def upscale(rgb,box,T=240,O=16):
    h,w,_=rgb.shape; out=cv2.resize(rgb,(w*2,h*2),interpolation=cv2.INTER_LANCZOS4).astype(np.float32); wsum=np.zeros((h*2,w*2,1),np.float32); acc=np.zeros_like(out)
    x0,y0,x1,y1=box
    ys=list(range(y0,y1,T)); xs=list(range(x0,x1,T))
    for ty in ys:
        for tx in xs:
            a,b=max(0,ty-O),min(h,ty+T+O); c,d=max(0,tx-O),min(w,tx+T+O)
            up=sr.upsample(cv2.cvtColor(rgb[a:b,c:d],cv2.COLOR_RGB2BGR)); up=cv2.cvtColor(up,cv2.COLOR_BGR2RGB).astype(np.float32)
            wt=np.ones(up.shape[:2],np.float32); f=O*2
            ramp=np.linspace(0,1,f,dtype=np.float32)
            if a>0: wt[:f]*=ramp[:,None]
            if b<h: wt[-f:]*=ramp[::-1][:,None]
            if c>0: wt[:,:f]*=ramp[None,:]
            if d<w: wt[:,-f:]*=ramp[::-1][None,:]
            acc[a*2:b*2,c*2:d*2]+=up*wt[...,None]; wsum[a*2:b*2,c*2:d*2]+=wt[...,None]
    return np.where(wsum>0.999,acc/np.maximum(wsum,1e-6),out*(1-wsum)+acc)
ref=np.asarray(Image.open(I+'st03-front-v2.webp').convert('RGB')); mr,lr=skin_simple(ref); tgt=med(lr,mr)
for src,name in [('st374-v3-front','front'),('st374-v2-side','side'),('st374-v2-back','back'),('st374-v2-pose','pose')]:
    t=time.time(); im=np.asarray(Image.open(I+src+'.webp').convert('RGB'))
    m,lab=skin(im); s=med(lab,m); d=tgt-s; dd=np.array([d[0]*0.5,d[1],d[2]],np.float32)       # B안
    w=ndi.gaussian_filter(m.astype(np.float32),2.5)[...,None]
    toned=cv2.cvtColor(np.clip(lab+dd[None,None,:]*w,0,255).astype(np.uint8),cv2.COLOR_LAB2RGB)
    alpha,ratio=bg_alpha(im.astype(np.float32))
    ys,xs=np.where(alpha>0.05); box=(max(0,xs.min()-8),max(0,ys.min()-8),min(900,xs.max()+8),min(1200,ys.max()+8))
    import os
    cache=f'out/up-{name}.png'
    if os.path.exists(cache): up=np.asarray(Image.open(cache).convert('RGB')).astype(np.float32)
    else:
        up=upscale(toned,box); Image.fromarray(up.clip(0,255).astype(np.uint8)).save(cache)
    a2=cv2.resize(alpha,(1800,2400),interpolation=cv2.INTER_CUBIC).clip(0,1)[...,None]
    rng=np.random.default_rng(374); grain=rng.normal(0,1.6,(2400,1800,1)).astype(np.float32)        # 아주 옅은 필름 입자(피사체에만)
    r2=cv2.resize(ratio,(1800,2400),interpolation=cv2.INTER_CUBIC).clip(0.8,1)[...,None]
    comp=(up+grain*a2)*a2+(BG*r2)*(1-a2)
    big=Image.fromarray(comp.clip(0,255).astype(np.uint8))
    m13=big.resize((1350,1800),Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.0,percent=35,threshold=2))
    m13.save(f'out/st374-v4-{name}.webp',quality=92,method=6)
    big.resize((900,1200),Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=0.8,percent=30,threshold=2)).save(f'out/st374-v4-{name}-900.webp',quality=88,method=6)
    big.resize((360,480),Image.LANCZOS).save(f'out/st374-v4-{name}-thumb.webp',quality=84,method=6)
    print(name,'box',box,'delta',dd.round(1),round(time.time()-t),'s',flush=True)
print('DONE',flush=True)
