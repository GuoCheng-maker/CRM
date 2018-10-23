from django.conf.urls import url
from django.shortcuts import HttpResponse, render, redirect
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.forms import ModelForm
from django.forms import widgets as wid
from stark.utils.page import Pagination
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.related import ForeignKey


class ShowList(object):
    '''
    将展示页面的表头和数据封装到这个类中，分别调用方法返回列表
    '''

    def __init__(self, config, data_list, request):
        self.config = config
        self.data_list = data_list
        self.request = request

        # 加入分页器
        data_count = self.data_list.count()
        current_page = int(self.request.GET.get("page", 1))
        base_path = self.request.path

        self.pagination = Pagination(current_page, data_count, base_path, self.request.GET, per_page_num=6,
                                     pager_count=11, )
        # 将数据进行分页
        self.page_Data = self.data_list[self.pagination.start:self.pagination.end]

        # actions(批量操作)
        self.actions = self.config.get_new_actions()

    def get_filter_linktags(self):
        link_dict = {}

        for filter_field in self.config.list_filter:
            import copy
            import urllib.parse
            params = copy.deepcopy(self.request.GET)

            print("params", params)  # params，初始为空 <QueryDict: {'publish': ['1'], 'authors': ['3']}>

            # 得到前端传过来的过滤字段的值。
            cid = self.request.GET.get(filter_field, 0)
            print("cid", cid)
            filter_field_obj = self.config.model._meta.get_field(filter_field)  # 通过字符串得到字段的方法

            # 注意此处(新版本做了修改。filter_field_obj.remote_field.model.objects.all())
            if isinstance(filter_field_obj, ManyToManyField) or isinstance(filter_field_obj, ForeignKey):
                # 如果是外键和多对多的话，直接利用方法获取到数据
                data_list = filter_field_obj.remote_field.model.objects.all()
            else:
                # 如果只是普通字段的话，那么获得的是主键的值和要过滤的字段的值。
                data_list = self.config.model.objects.all().values("pk", filter_field)
                print("data_list", data_list)  # {'pk': 13, 'title': '金银岛'}

            # 处理"全部"标签
            temp = []
            if params.get(filter_field):
                del params[filter_field]
                temp.append(mark_safe("<a href='?%s'>全部<a>" % urllib.parse.urlencode(params)))
            else:
                temp.append(mark_safe("<a class='active' href=''>全部<a>"))

            # 处理数据标签
            for obj in data_list:
                if isinstance(filter_field_obj, ForeignKey) or isinstance(filter_field_obj, ManyToManyField):
                    pk = obj.pk
                    text = str(obj)
                    params[filter_field] = pk

                else:  # data_list= [{"pk":1,"title":"go"},....]
                    pk = obj.get("pk")
                    text = obj.get(filter_field)
                    params[filter_field] = text

                _url = urllib.parse.urlencode(params)
                if cid == str(pk) or cid == text:
                    # 如果传过来一个值和主键相等或者值为上面的text值相等的话，前端渲染一个选中红色的URL的a标签.
                    link_tag = mark_safe("<a class='active' href='?%s'>%s </a>" % (_url, text))
                else:
                    # 没有active,表示没有选中。
                    link_tag = mark_safe("<a href='?%s'>%s </a>" % (_url, text))
                temp.append(link_tag)

            link_dict[filter_field] = temp

        return link_dict

    # 获取操作列表
    def get_action_list(self):
        temp = []
        for action in self.actions:
            temp.append({
                "name": action.__name__,  # 通过__name__可以获取函数的名字字符串。
                "desc": action.short_description  # 获取方法名的中文介绍。
            })
            # [{"name":patch_init,"desc":"批量初始化"}]
        return temp

    # 构建表头数据
    def get_header(self):

        header_list = []
        for field in self.config.new_list_display():
            if callable(field):
                val = field(self, header=True)
                header_list.append(val)
            else:
                if field == "__str__":
                    header_list.append(self.config.model._meta.model_name.upper())
                else:
                    val = self.config.model._meta.get_field(field).verbose_name
                    header_list.append(val)
        return header_list

    # 构建表单数据
    def get_body(self):
        new_data_list = []
        for obj in self.page_Data:
            temp = []
            for field in self.config.new_list_display():

                if callable(field):
                    val = field(self.config, obj)
                else:
                    try:
                        field_obj = self.config.model._meta.get_field(field)
                        # 展示多对多字段的处理方式取值。
                        if isinstance(field_obj, ManyToManyField):
                            ret = getattr(obj, field).all()
                            t = []
                            for mobj in ret:
                                t.append(str(mobj))
                            # 用","进行拼接多个字段。
                            val = ",".join(t)

                        else:
                            if field_obj.choices:
                                #这里可以对有choice字段的做一个判断，返回的choice的值而不是序号。
                                val = getattr(obj, "get_"+field+"_display")
                            else:
                                val = getattr(obj, field)
                            if field in self.config.list_display_links:
                                _url = self.config.get_change_url(obj)
                                val = mark_safe("<a href='%s'>%s</a>" % (_url, val))
                    except Exception as e:
                        val = getattr(obj, field)
                temp.append(val)

            new_data_list.append(temp)
        return new_data_list


class ModelStark(object):
    list_display_links = []
    list_display = ["__str__"]
    modelform_class = []
    serach_fields = []
    list_filter = []
    actions = []

    # 系统自带的批量删除函数
    def path_delete(self, request, queryset):
        queryset.delete()

    path_delete.short_description = "批量删除"

    def __init__(self, model, site):
        self.model = model
        self.site = site

    # 渲染一个选择框
    def checkbox(self, obj=None, header=False):
        if header:
            return mark_safe("<input id='choice' type='checkbox'>选择")
        return mark_safe("<input class='choice_item' value='%s' type='checkbox' name='selected_pk'>" % obj.pk)

    # 渲染一个编辑按钮
    def edit(self, obj=None, header=False):
        if header:
            return "操作"
        _url = self.get_change_url(obj)
        return mark_safe("<a href='%s' class='btn btn-info'>编辑</a>" % _url)

    # 渲染一个删除按钮
    def deletes(self, obj=None, header=False):
        if header:
            return "操作"

        _url = self.get_delete_url(obj)
        return mark_safe("<a href='%s' class='btn btn-danger'>删除</a>" % _url)

    # 返回一个反向解析得到的change_url
    def get_change_url(self, obj):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label

        _url = reverse("%s_%s_change" % (app_label, model_name), args=(obj.pk,))

        return _url

    # 返回一个反向解析得到的delete_url
    def get_delete_url(self, obj):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label

        _url = reverse("%s_%s_delete" % (app_label, model_name), args=(obj.pk,))

        return _url

    # 返回一个反向解析得到的add_url
    def get_add_url(self):

        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label

        _url = reverse("%s_%s_add" % (app_label, model_name))

        return _url

    # 得到查看页面的url.
    def get_list_url(self):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        _url = reverse("%s_%s_list" % (app_label, model_name))
        return _url

    # 将自带删除写入，并且将定制的加入，返回批量操作的方法列表
    def get_new_actions(self):
        temp = []
        temp.append(ModelStark.path_delete)
        temp.extend(self.actions)
        return temp

    # 将自带展示写入，并且将定制的加入，返回展示的字段列表
    def new_list_display(self):
        temp = []
        temp.append(ModelStark.checkbox)
        temp.extend(self.list_display)
        if not self.list_display_links:
            temp.append(ModelStark.edit)
        temp.append(ModelStark.deletes)
        return temp

    # 将自带的modelform 加入，如果自定制了则使用自定制的
    def get_modelform_class(self):
        if not self.modelform_class:
            class ModelFormDemo(ModelForm):
                class Meta:
                    model = self.model
                    fields = "__all__"

            return ModelFormDemo
        else:
            return self.modelform_class

    # 增加数据视图函数
    def add_view(self, request):
        ModelFormDemo = self.get_modelform_class()
        form = ModelFormDemo()

        # 循环每个form字段，看看他们的类型是不是一对多和对多类型，是的话需要前端添加+号
        for bfield in form:
            print(bfield.field)  # 字段对象
            print(bfield.name)  # 字段名（字符串）
            from django.forms.models import ModelChoiceField
            if isinstance(bfield.field, ModelChoiceField):
                bfield.is_pop = True
                print(bfield.field.queryset.model)
                related_model_name = bfield.field.queryset.model._meta.model_name
                related_app_label = bfield.field.queryset.model._meta.app_label

                _url = reverse("%s_%s_add" % (related_app_label, related_model_name))
                bfield.url = _url + "?pop_res_id=id_%s" % bfield.name
        if request.method == "POST":
            form = ModelFormDemo(request.POST)
            if form.is_valid():
                obj = form.save()
                pop_res_id = request.GET.get("pop_res_id")
                if pop_res_id:
                    res = {"pop_res_id": pop_res_id, "pk": obj.pk, "text": str(obj)}
                    return render(request, "pop.html", locals())
                else:
                    return redirect(self.get_list_url())

        return render(request, "add_view.html", locals())

    # 编辑数据视图函数
    def change_view(self, request, id):
        ModelFormDemo = self.get_modelform_class()
        edit_obj = self.model.objects.filter(pk=id).first()
        if request.method == "POST":
            form = ModelFormDemo(request.POST, instance=edit_obj)
            if form.is_valid():
                form.save()
                return redirect(self.get_list_url())
            else:
                return render(request, "add_view.html", locals())

        form = ModelFormDemo(instance=edit_obj)
        return render(request, "change_view.html", locals())

    # 删除数据视图函数
    def delete_view(self, request, id):
        url = self.get_list_url()
        if request.method == "POST":
            self.model.objects.filter(pk=id).delete()
            return redirect(url)

        return render(request, "delete_view.html", locals())

    # 得到搜索的字段，封装成一个"或"关系的Q对象返回。
    def get_serach_conditon(self, request):
        key_word = request.GET.get("q", "")
        self.key_word = key_word
        from django.db.models import Q
        search_connection = Q()
        if key_word:
            # self.search_fields # ["title","price"]
            search_connection.connector = "or"
            # 在这里组建一个Q对象，需要将列表内的字符串把引号去掉，并且这个Q对象是或的关系，最后返回
            for search_field in self.serach_fields:
                search_connection.children.append((search_field + "__contains", key_word))
        return search_connection

    # 得到过滤的字段，封装成一个"和"关系的Q对象返回。
    def get_filter_condition(self, request):
        from django.db.models import Q
        filter_condition = Q()
        for filter_field, val in request.GET.items():
            # if filter_field in self.list_filter:
            if filter_field != "page":
                filter_condition.children.append((filter_field, val))
        return filter_condition

    # 最难的查看数据的视图函数。
    def list_view(self, request):
        if request.method == "POST":
            print(request.POST)
            action = request.POST.get("action")
            select_pk = request.POST.getlist("selected_pk")
            queryset = self.model.objects.filter(pk__in=select_pk)
            action_func = getattr(self, action)
            action_func(request, queryset)

        # 获取Q对象。
        search_connection = self.get_serach_conditon(request)

        filter_condition = self.get_filter_condition(request)

        # 获取当前表筛选之后的数据，没有筛选条件则为全部
        data_list = self.model.objects.all().filter(search_connection).filter(filter_condition)

        # 按这个类的方法进行展示
        showlist = ShowList(self, data_list, request)

        # 构建一个查看URL
        add_url = self.get_add_url()
        return render(request, "list_view.html", locals())

    def extra_url(self):
        return []
    # 将增删改查4个URL封装成一个列表
    def get_urls2(self):
        temp = []
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        temp.append(url(r"^add/", self.add_view, name="%s_%s_add" % (app_label, model_name)))
        temp.append(url(r"^$", self.list_view, name="%s_%s_list" % (app_label, model_name)))
        temp.append(url(r"^(\d+)/delete/", self.delete_view, name="%s_%s_delete" % (app_label, model_name)))
        temp.append(url(r"^(\d+)/change/", self.change_view, name="%s_%s_change" % (app_label, model_name)))
        temp.extend(self.extra_url())
        return temp

    @property
    def urls2(self):
        return self.get_urls2(), None, None


class StarkSite(object):
    def __init__(self):
        self._registry = {}

    def register(self, model, stark_class=None):
        if not stark_class:
            stark_class = ModelStark
        self._registry[model] = stark_class(model, self)

    def get_urls(self):
        temp = []
        for model, stark_class_obj in self._registry.items():
            model_name = model._meta.model_name
            app_label = model._meta.app_label

            temp.append(url(r"^%s/%s/" % (app_label, model_name), stark_class_obj.urls2))
        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


# admin的单例对象，整个程序都使用的是这一个。
site = StarkSite()
