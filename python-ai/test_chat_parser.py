# -*- coding: utf-8 -*-
"""聊天记录解析测试用例：读取本地文件测试，验证TXT/XML解析、准确率≥95%、缓存功能"""
import os
from core import wechat_chat_parser
from utils import logger
from config import settings

# -------------------------- 配置项（请修改为你的本地文件路径） --------------------------
# 填写你的本地测试文件路径，支持无时间戳/带时间戳TXT、XML格式
TEST_TXT_FILE_PATH = "./test_chat_record.txt"  # 你的微信TXT聊天记录文件
TEST_XML_FILE_PATH = ""  # 你的微信XML聊天记录文件（可选，无则注释）
# ----------------------------------------------------------------------------------------

def read_local_file(file_path: str) -> str:
    """
    读取本地文件内容（支持TXT/XML），做基础编码处理
    :param file_path: 文件绝对/相对路径
    :return: 文件内容字符串
    :raise: 文件不存在/读取失败抛出异常
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"测试文件不存在：{file_path}")
    # 尝试多种常见编码读取，兼容微信导出的不同编码格式
    encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read().strip()
            logger.info(f"成功读取本地文件：{file_path}，使用编码：{encoding}")
            return content
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"文件{file_path}编码不支持，无法读取（已尝试：{encodings}）")

# 验证解析准确率（核心测试：读取本地文件，验证解析准确率）
def test_parse_accuracy():
    """读取本地TXT/XML文件，测试解析准确率、格式识别等"""
    logger.info(f"===== 开始读取本地文件验证解析准确率 =====")
    test_result = {
        "txt_parse": {"status": "未测试"},
        "xml_parse": {"status": "未测试"},
        "overall_status": "未测试"
    }

    # 测试TXT文件（必测）
    if os.path.exists(TEST_TXT_FILE_PATH):
        try:
            txt_content = read_local_file(TEST_TXT_FILE_PATH)
            txt_result = wechat_chat_parser.parse(txt_content, "txt", use_cache=False)
            test_result["txt_parse"] = {
                "file_path": TEST_TXT_FILE_PATH,
                "total_raw": txt_result["data"]["stats"]["total_raw"],
                "total_clean": txt_result["data"]["stats"]["total_clean"],
                "accuracy": txt_result["data"]["stats"]["accuracy"],
                "parse_time": txt_result["data"]["stats"]["parse_time"],
                "format_type": txt_result["data"]["stats"]["format_type"],
                "status": "达标" if txt_result["data"]["stats"]["accuracy"] >= 95 else "不达标"
            }
        except Exception as e:
            test_result["txt_parse"] = {
                "file_path": TEST_TXT_FILE_PATH,
                "status": "测试失败",
                "error": str(e)[:100]
            }
            logger.error(f"TXT文件测试失败：{e}", exc_info=True)
    else:
        test_result["txt_parse"]["status"] = "文件不存在，跳过测试"

    # 测试XML文件（可选，无则跳过）
    if 'TEST_XML_FILE_PATH' in locals() and os.path.exists(TEST_XML_FILE_PATH):
        try:
            xml_content = read_local_file(TEST_XML_FILE_PATH)
            xml_result = wechat_chat_parser.parse(xml_content, "xml", use_cache=False)
            test_result["xml_parse"] = {
                "file_path": TEST_XML_FILE_PATH,
                "total_raw": xml_result["data"]["stats"]["total_raw"],
                "total_clean": xml_result["data"]["stats"]["total_clean"],
                "accuracy": xml_result["data"]["stats"]["accuracy"],
                "parse_time": xml_result["data"]["stats"]["parse_time"],
                "format_type": xml_result["data"]["stats"]["format_type"],
                "status": "达标" if xml_result["data"]["stats"]["accuracy"] >= 95 else "不达标"
            }
        except Exception as e:
            test_result["xml_parse"] = {
                "file_path": TEST_XML_FILE_PATH,
                "status": "测试失败",
                "error": str(e)[:100]
            }
            logger.error(f"XML文件测试失败：{e}", exc_info=True)
    else:
        test_result["xml_parse"]["status"] = "文件不存在，跳过测试"

    # 验证整体达标状态
    txt_ok = test_result["txt_parse"]["status"] == "达标"
    xml_ok = test_result["xml_parse"]["status"] in ["达标", "未测试", "文件不存在，跳过测试"]
    test_result["overall_status"] = "全部达标" if (txt_ok and xml_ok) else "部分不达标/测试失败"

    # 打印详细测试结果
    logger.info(f"===== 本地文件解析准确率验证结果 =====")
    for fmt, res in test_result.items():
        if fmt == "overall_status":
            logger.info(f"📊 整体测试状态：{res}")
        else:
            logger.info(f"\n{fmt.upper()} 测试详情：")
            for k, v in res.items():
                logger.info(f"  {k}: {v}")
    return test_result

# 测试缓存功能（使用本地TXT文件片段测试，避免大文件缓存）
def test_cache():
    """测试LRU缓存功能，验证缓存命中/未命中结果一致性"""
    logger.info(f"===== 开始测试缓存功能 =====")
    if not os.path.exists(TEST_TXT_FILE_PATH):
        logger.warning(f"TXT测试文件不存在，跳过缓存测试")
        return
    # 读取文件前1000个字符作为缓存测试用例（避免大文件缓存占用空间）
    try:
        txt_content = read_local_file(TEST_TXT_FILE_PATH)[:1000]
        # 第一次解析（缓存未命中）
        res1 = wechat_chat_parser.parse(txt_content, "txt", use_cache=True)
        # 第二次解析（缓存命中）
        res2 = wechat_chat_parser.parse(txt_content, "txt", use_cache=True)
        # 验证核心结果一致
        assert res1["code"] == res2["code"], "缓存前后响应码不一致"
        assert res1["data"]["records"] == res2["data"]["records"], "缓存前后解析记录不一致"
        assert res1["data"]["stats"]["accuracy"] == res2["data"]["stats"]["accuracy"], "缓存前后准确率不一致"
        logger.info("✅ 缓存测试通过：两次解析结果完全一致，缓存命中正常")
    except Exception as e:
        logger.error(f"❌ 缓存测试失败：{e}", exc_info=True)
        raise

# 测试单条异常记录（确保异常记录不影响整体解析，独立测试）
def test_single_error_record():
    """测试混合正常/异常记录的解析，确保异常记录自动跳过"""
    logger.info(f"===== 开始测试单条异常记录解析 =====")
    # 混合正常+异常+系统消息的测试用例（覆盖时间错误、系统消息、空内容）
    test_txt = """
Carlotta:
拿到手有点跃跃欲试的感觉

根号3。1:
崭新出厂哦

【无效时间】测试:
异常记录（时间格式错误）

根号3。1:
撤回了一条消息

小明:

根号3。1:
其实也就是济州岛和新马泰了
    """
    res = wechat_chat_parser.parse(test_txt, "txt", use_cache=False)
    # 验证有效记录数为3（Carlotta1条 + 根号3。1有效2条，过滤异常/系统/空记录）
    valid_count = len(res["data"]["records"])
    expected_count = 3
    assert valid_count == expected_count, \
        f"❌ 单条异常记录测试失败，预期{expected_count}条有效记录，实际{valid_count}条"
    logger.info(f"✅ 单条异常记录测试通过：有效记录{valid_count}条，异常/系统记录已自动过滤")

if __name__ == "__main__":
    try:
        # 1. 核心：读取本地文件验证解析准确率
        test_parse_accuracy()
        # 2. 测试缓存功能
        test_cache()
        # 3. 测试异常记录解析（独立用例）
        test_single_error_record()

        logger.info(f"\n===== 🎉 所有测试用例执行完成 =====")
    except Exception as e:
        logger.error(f"\n===== ❌ 测试用例执行失败：{e} =====", exc_info=True)