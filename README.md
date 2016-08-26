# sayit       
学习 flask 项目，一个简单的论坛。

## 已有功能
- 注册、登录、找回密码、激活邮件、灌水限制        
- 赞、关注、收藏主题，赞回复，屏蔽、关注用户，异步后续通知
- 简单验证码， 使用 [pillow](https://github.com/python-pillow/Pillow) 
- 使用七牛保存主题图片附件以及用户头像
  - 附件单纯前端上传，后端保存相关信息
  - 头像后端异步上传          
- redis 计数器和缓存热数据          
- markdown 支持，使用 [misaka](https://github.com/FSX/misaka)       
  - 编辑主题可在线预览  
- @用户，使用 [at.js](https://github.com/ichord/At.js)          
- 代码高亮，使用 [highlight.js](https://highlightjs.org/)         
- 时间格式化，使用 [Moment.js](http://momentjs.com/)

## 待实现
- admin 面板      
- 细化用户权限           
- 搜索       

## 测试运行 
git clone         
安装依赖包              
`config.py.sample` 改名，修改 mysql, redis 配置    
跑一遍单元测试   
```bash
export FLKCONF="test"                            
python manage.py test     
```   
没有出错接着生成假数据      
```bash   
export FLKCONF="dev"                             
python manage.py fake_site          
```            
基本浏览      
`python manage.py runserver`                    
测试赞关注等异步功能需要 celery       
```bash   
export FLKCONF="dev"    
celery -A sayit.celery_worker.celery worker -l info --purge              
celery beat --app sayit.celery_worker.celery  #定时保存点击数      
```    