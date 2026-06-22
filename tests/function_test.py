#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/6/22 10:26
# @Author  : 19921224
# @File    : function_test.py
# @Software: PyCharm
# @Description: 功能测试

from urllib.parse import urlparse

url = "http://wwww.baidu.com"

print(urlparse(url))

if __name__ == "__main__":
    print("测试结束")