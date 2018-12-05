from django.shortcuts import render,redirect,HttpResponse
from django.contrib import  auth
from blog import models
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
import json

def login(request):
    if request.method=='GET':
        return render(request,'login.html')
    if request.method=='POST':
        username=request.POST.get('username')
        password=request.POST.get('password')
        user=auth.authenticate(username=username,password=password)
        if user:
            auth.login(request,user)
            return redirect('/index/')
        else:
            return render(request,'login.html')

def index(request):
    article_list=models.Article.objects.all()
    return render(request,'index.html',{'article_list':article_list})

def logout(request):
    auth.logout(request)
    return redirect('/index/')

def homesite(request,username,**kwargs):
    user = models.UserInfo.objects.filter(username=username).first()
    if not user:
        return render(request, "not_found.html")
    # 查询当前站点对象
    blog = user.blog
    # 查询当前用户发布的所有文章
    if not kwargs:
        article_list = models.Article.objects.filter(user__username=username)
    else:
        condition=kwargs.get('condition')
        params=kwargs.get('params')
        if condition=='category':
            article_list = models.Article.objects.filter(user__username=username).filter(category__title=params)
        elif condition=='tag':
            article_list = models.Article.objects.filter(user__username=username).filter(tags__title=params)
        else:
            year,month=params.split('/')
            article_list = models.Article.objects.filter(user__username=username).filter(create_time__year=year,create_time__month=month)
    if not article_list:
        return render(request,'not_found.html')
    return render(request,'homesite.html',locals())

def article_detail(request,username,article_id):
    user = models.UserInfo.objects.filter(username=username).first()
    # 查询当前站点对象
    blog = user.blog
    article_obj = models.Article.objects.filter(pk=article_id).first()
    comment_list=models.Comment.objects.filter(article_id=article_id).all()
    return render(request,'article_detail.html',locals())

def digg(request):
    '''
    点赞
    :param request:
    :return:
    '''
    is_up=json.loads(request.POST.get('is_up'))
    article_id=request.POST.get('article_id')
    user_id=request.user.pk
    response={'state':True,'msg':None}
    obj=models.ArticleUpDown.objects.filter(user_id=user_id,article_id=article_id).first()
    if obj:
        response['state']=False
        response['handled']=obj.is_up
    else:
        with transaction.atomic():
            new_obj=models.ArticleUpDown.objects.create(user_id=user_id,article_id=article_id,is_up=is_up)
            if is_up:
                models.Article.objects.filter(pk=article_id).update(up_count=F('up_count')+1)
            else:
                models.Article.objects.filter(pk=article_id).update(down_count=F('down_count')+1)
    return JsonResponse(response)

def comment(request):
    '''
    评论
    :param request:
    :return:
    '''
    user_id=request.user.pk
    article_id=request.POST.get('article_id')
    content=request.POST.get('content')
    pid=request.POST.get('pid')
    with transaction.atomic():
        comment=models.Comment.objects.create(user_id=user_id,article_id=article_id,content=content,parent_comment_id=pid)
        models.Article.objects.filter(pk=article_id).update(comment_count=F('comment_count')+1)
    response={'state':True}
    response['timer']=comment.create_time.strftime('%Y-%m-%d %X')
    response['content']=comment.content
    response['user']=request.user.username
    return JsonResponse(response)

def backend(request):
    '''
    后台管理
    :param request:
    :return:
    '''
    user=request.user
    article_list=models.Article.objects.filter(user=user)
    return render(request,'backend/backend.html',locals())
from bs4 import BeautifulSoup
def add_article(request):
    '''
    添加文章
    :param request:
    :return:
    '''
    if request.method=='POST':
        title=request.POST.get('title')
        content=request.POST.get('content')
        user=request.user
        cate_pk=request.POST.get('cate')
        tags_pk_list=request.POST.getlist('tags')
        soup=BeautifulSoup(content,"html.parser")
        #文章过滤
        for tag in soup.find_all():
            if tag.name in ['script',]:
                tag.decompose()
        #文章切片
        desc=soup.text[0:150]
        #文章导入到数据库中
        with transaction.atomic():
            article_obj=models.Article.objects.create(title=title,content=str(soup),user=user,category_id=cate_pk,desc=desc)
            for tag_pk in tags_pk_list:
                models.Article2Tag.objects.create(article_id=article_obj.pk,tag_id=tag_pk)
        return redirect('/backend/')
    else:
        blog=request.user.blog
        cate_list=models.Category.objects.filter(blog=blog)
        tags=models.Tag.objects.filter(blog=blog)

        return render(request,'backend/add_article.html',locals())

from cnblog import settings
import os,json
def upload(request):
    '''
    文章中上传图片
    :param request:
    :return:
    '''
    img_obj=request.FILES.get('upload_img')
    img_name=img_obj.name
    path=os.path.join(settings.BASE_DIR,'static','upload',img_name)
    with open(path,'wb') as f:
        for line in img_obj:
            f.write(line)
    res={'error':0,'url':'/static/upload/'+img_name}
    return HttpResponse(json.dumps(res))
