#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/7/1 15:49
# @Author  : 19921224
# @File    : api.py
# @Software: PyCharm
# @Description: 读取 最新的 apis/xxx.json 解析接口文件

import json


def parse_apis(file_path=r"apis/20260702-api.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        obj = json.load(f)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            if 'apis' in obj:
                return obj['apis']
            return [obj]
        raise TypeError(f"JSON根节点类型不支持： {type(obj)}")


if __name__ == "__main__":
    # 用法自测
    file_path = r"apis/20260701-api.json"
    dict_list = parse_apis(file_path)
    print(type(dict_list), len(dict_list))
    # print(dict_list[0])
    # print(json.dumps(dict_list, ensure_ascii=False, indent=2))
    for item in dict_list:
        print(item)
    current_default_choice_text = dict_list[0].get("name")
    print(f"current_default_choice_text: {current_default_choice_text}")
    print(f"current_default_choice = {current_default_choice_text} ✅ (推荐使用)")