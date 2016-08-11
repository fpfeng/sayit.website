# sayit       
学习 flask 项目，一个简单的论坛，左抄右抄大杂烩。

## 大概正常的功能
注册、登录、找回密码        
发表主题回复（废话）       
markdown 支持        
灌水限制           
赞、关注、收藏主题，赞回复，屏蔽、关注用户，异步后续通知   
七牛保存头像，异步上传          
redis 缓存计数器和热数据         
简单验证码      
激活邮件         
@用户，使用 [at.js](https://github.com/ichord/At.js)          
代码高亮，使用 [highlight.js](https://highlightjs.org/)         
时间格式化，使用 [Moment.js](http://momentjs.com/)

## 待实现
admin 面板      
细化用户权限      
图片附件             
实时预览 markdown       
搜索       

## 测试运行 
git clone         
安装依赖包              
`config.py.sample` 改名，修改 mysql, redis 配置    
跑一编单元测试   
```bash
export FLKCONF="test"                            
python manage.py test     
```   
没有出错接着生成假数据      
```bash   
export FLKCONF="dev"                             
python manage.py fake_site          
```            
基本浏览运行      
`python manage.py runserver`                    
测试赞关注等功能需要 celery       
```bash   
export FLKCONF="dev"    
celery -A sayit.celery_worker.celery worker -l info --purge              
celery beat --app sayit.celery_worker.celery  #定时保存点击数      
```    