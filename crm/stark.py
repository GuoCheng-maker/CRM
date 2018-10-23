# Author:Jesi
# Time : 2018/10/1 9:14
from stark.service.stark import site,ModelStark
from crm.models import *
from django.utils.safestring import mark_safe
from django.conf.urls import url
from django.shortcuts import render,HttpResponse,redirect
from django.http import JsonResponse
import json
import datetime
from django.db.models import Q

site.register(School)


class UserConfig(ModelStark):
    list_display = ["name","email","depart"]
site.register(UserInfo,UserConfig)


class ClassConfig(ModelStark):
    def display_classname(self,obj=None,header=False):
        if header:
            return "班级名称"
        class_name="%s(%s)"%(obj.course.name,str(obj.semester))
        return class_name

    list_display = [display_classname,"tutor","teachers"]
site.register(ClassList,ClassConfig)


class CustomerConfig(ModelStark):


    def cancel_course(self,request,customer_id,course_id):
        # print(customer_id,course_id)
        obj=self.model.objects.filter(pk=customer_id).first()   #取到这个对象
        obj.course.remove(course_id)    #把对象通过字段找到的课程remove掉，传入remove的课程ID
        return redirect(self.get_list_url())

    def public_customer(self,request):
        now=datetime.datetime.now()
        delta_day3=datetime.timedelta(days=3)
        delta_day15=datetime.timedelta(days=15)
        customer_list=Customer.objects.filter(Q(last_consult_date__lt=now-delta_day3)|Q(recv_date__lt=now-delta_day15),status=2)
        return render(request,"public.html",locals())

    def futher(self,request,customer_id):
        user_id=3  #这个是当前登录销售的id。
        delta_day3 = datetime.timedelta(days=3)
        delta_day15 = datetime.timedelta(days=15)
        now=datetime.datetime.now()
        #为该客户更改课程顾问和对应的时间。
        ret=Customer.objects.filter(pk=customer_id).filter(Q(last_consult_date__lt=now - delta_day3) | Q(recv_date__lt=now - delta_day15), status=2).update(consultant=user_id,last_consult_date=now,recv_date=now)
        if  not ret:
            return HttpResponse("已经被跟进！")
            #在新建的表中创建一条记录表示别的销售接单，开始跟进。
        CustomerDistrbute.objects.create(customer_id=customer_id,consultant_id=user_id,status=1,date=now)
        return HttpResponse("跟进成功！")


    def mycustomer(self,request):
        user_id=3
        customer_distrbute_list=CustomerDistrbute.objects.filter(consultant_id=user_id)
        return render(request,"mycustomer.html",locals())


    def extra_url(self):
        temp=[]
        temp.append(url(r'cancel_course/(\d+)/(\d+)',self.cancel_course))
        temp.append(url(r'public/',self.public_customer))
        temp.append(url(r'futher/(\d+)',self.futher))
        temp.append(url(r'mycustomer/',self.mycustomer))
        return temp

    def display_course(self,obj=None,header=False):
        #通过这个方法，可以取到对应的choice的值，而不是序号1或者2
        if header:
            return "咨询课程"
        else:
            temp=[]
            #这里的obj是customer表的实例对象，也就是当前记录的对象
            #对象正向查询按字段，直接.字段名.all()取出所有课程对象。
            #然后course.name取到所有的课程。
            for course in obj.course.all():
                s = "<a href='/stark/crm/customer/cancel_course/%s/%s' style='border:1px solid #369;padding:3px 6px'><span>%s</span></a>&nbsp;" %(obj.pk, course.pk, course.name)
                temp.append(s)

            return mark_safe("".join(temp))

    list_display = ["name", "gender",display_course,"consultant"]
site.register(Customer,CustomerConfig)


site.register(Department)


site.register(Course)


class ConsultConfig(ModelStark):
    list_display = ["customer","consultant","date","note"]
site.register(ConsultRecord,ConsultConfig)


class CourseRecordConfig(ModelStark):


    def score(self,request,course_record_id):
        if request.method == "POST":
            # 构建一个dict
            data = {}
            for key,value in request.POST.items():
                if key=="csrfmiddlewaretoken":
                    continue
                field,pk=key.rsplit("_",1)
                if pk in data:
                    data[pk][field]=value
                else:
                    data[pk]={field:value}

            for pk,update_data in data.items():
                StudyRecord.objects.filter(pk=pk).update(**update_data)
            return redirect(request.path)


        else:
            study_record_list=StudyRecord.objects.filter(course_record=course_record_id)
            record=StudyRecord.score_choices
            return render(request,"score.html",locals())

    def extra_url(self):
        temp=[]
        temp.append(url(r'record_score/(\d+)',self.score))
        return temp

    def record_score(self,obj=None,header=False):
        if header:
            return "录入成绩"
        return mark_safe("<a href='record_score/%s'>录入成绩</a>"%obj.pk)

    def record(self,obj=None,header=False):
        if header:
            return "考勤"
        return mark_safe("<a href='/stark/crm/studyrecord/?course_record=%s'>记录</a>"%obj.pk)

    list_display=["class_obj","day_num","teacher",record,record_score]

    def path_studyrecord(self, request, queryset):
        temp = []
        for course_record in queryset:
            #与course_record关联的班级对应的所有学生应该取出。
            #手里有一个课程的记录（python9期的94天课程），拿班级ID是这个记录的班级对象的主键值的学生过滤出来。
            student_list=Student.objects.filter(class_list__id=course_record.class_obj.pk)

            #用这些学生去创建一条条的StudyReord.
            for student in student_list:
                obj=StudyRecord(student=student,course_record=course_record)
                temp.append(obj)
        StudyRecord.objects.bulk_create(temp)
    path_studyrecord.short_description = "批量生成"
    actions = [path_studyrecord]
site.register(CourseRecord,CourseRecordConfig)


class StudyConfig(ModelStark):
    list_display = ["student","course_record","record","score"]
    def path_late(self, request, queryset):
        queryset.update(record="late")
    path_late.short_description = "迟到"
    actions = [path_late]
site.register(StudyRecord,StudyConfig)



class StudentConfig(ModelStark):
    def score_view(self,request,sid):
        if request.is_ajax():
            print("request.GET:",request.GET)
            print("request.body",request.body)
            cid=request.GET.get("cid")
            sid=request.GET.get("sid")
            study_record_list=StudyRecord.objects.filter(student=sid,course_record__class_obj=cid)
            data_list=[]
            for study_record in study_record_list:
                day_num=study_record.course_record.day_num
                data_list.append(["day%s"%day_num,study_record.score])

            return JsonResponse(data_list,safe=False)
        else:
            student=Student.objects.filter(pk=sid).first()
            class_list=student.class_list.all()
            return render(request,"score_view.html",locals())

    def extra_url(self):
        temp=[]
        temp.append(url('score_view/(\d+)',self.score_view))
        return temp

    def score_show(self,obj=None,header=False):
        if header:
            return "查看成绩"
        else:
            return mark_safe("<a href='score_view/%s'>查看成绩</a>"%obj.pk)
    list_display = ["customer","class_list",score_show]
    list_display_links = ["customer"]
site.register(Student,StudentConfig)