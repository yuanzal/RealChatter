# -*- coding: utf-8 -*-
"""聊天记录解析核心：支持微信2种TXT格式（带时间戳/无时间戳）+ XML，正则+清洗+缓存整合"""
import re
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime

from config import settings
from utils import logger, global_cache, generate_content_key

class WeChatChatParser:
    """微信纯文字聊天记录解析器：兼容2种TXT格式+XML，正则解析+数据清洗+异常处理"""
    def __init__(self):
        # 正则1：带时间戳格式【2025-02-03 18:00:00】张三：你好
        self.txt_pattern_with_time = re.compile(
            r"【(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s\d{1,2}:\d{1,2}(:\d{1,2})?)】([^：:]+)：([\s\S]*?)(?=【\d{4}|-{5,}|$)",
            re.MULTILINE | re.UNICODE
        )
        # 正则2：无时间戳极简格式 【核心优化】匹配时直接过滤发送人后无内容的空行
        # 新增 (?![\s\n]*$) 确保内容非空（排除纯换行/空格的空内容）
        self.txt_pattern_no_time = re.compile(
            r"([^：:\n]+)[：:]\s*([\s\S]*?)(?=[^：:\n]+[：:]|$)(?![\s\n]*$)",
            re.MULTILINE | re.UNICODE
        )
        # 去重唯一键模板：时间+发送人+内容（避免重复解析）
        self.duplicate_key_template = "{time}_{sender}_{content}"
        # 无时间戳记录默认补充时间（当前解析时间，保证数据结构统一）
        self.default_time = datetime.now().strftime(settings.PARSE_TIME_FORMAT)
        # 初始化解析统计
        self.parse_stats = {
            "total_raw": 0,
            "total_clean": 0,
            "filter_count": 0,
            "accuracy": 0.0,
            "parse_time": 0.0,
            "format_type": ""  # 新增：标记实际解析的格式（txt_with_time/txt_no_time/xml）
        }
        # 新增：微信媒体/表情匹配正则（用于区分纯媒体和带内容的媒体）
        self.wechat_media_pattern = re.compile(r"\[图片|视频|语音|文件|小程序|红包|转账\]")
        self.wechat_emo_pattern = re.compile(r"\[.+?\]")
        # 新增：无意义内容过滤（单字符/纯符号，可自定义添加）
        self.nonsense_pattern = re.compile(r"^[\w\d]{1}$|^[^a-zA-Z0-9\u4e00-\u9fff]+$")

    def _standardize_time(self, raw_time: str) -> str:
        """
        时间标准化：统一转换为settings.PARSE_TIME_FORMAT（%Y-%m-%d %H:%M:%S）
        :param raw_time: 原始时间字符串，空则返回默认时间
        """
        if not raw_time:
            return self.default_time
        # 尝试多种常见格式解析
        time_formats = [
            settings.PARSE_TIME_FORMAT,
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M"
        ]
        for fmt in time_formats:
            try:
                dt = datetime.strptime(raw_time.strip(), fmt)
                return dt.strftime(settings.PARSE_TIME_FORMAT)
            except ValueError:
                continue
        logger.warning(f"无法标准化时间：{raw_time}，使用默认时间")
        return self.default_time

    def _filter_invalid_content(self, content: str) -> bool:
        """
        【新增核心方法】过滤无效内容：保留有效对话，过滤纯媒体/纯表情/无意义内容
        :param content: 清洗后的消息内容
        :return: True=有效内容，False=无效内容
        """
        # 1. 过滤空内容（已清洗后）
        if not content or content.strip() == "":
            return False
        content_strip = content.strip()
        # 2. 过滤纯微信媒体（[图片]/[视频]等，无其他文字）
        if self.wechat_media_pattern.fullmatch(content_strip):
            return False
        # 3. 过滤纯表情（仅[xxx]，无其他文字）
        if self.wechat_emo_pattern.fullmatch(content_strip):
            return False
        # 4. 过滤无意义内容（单字符/纯符号，可根据需要注释这行）
        # if self.nonsense_pattern.fullmatch(content_strip):
        #     return False
        # 5. 有效内容，保留
        return True

    def _filter_system_message(self, content: str) -> bool:
        """
        过滤系统消息：仅精准过滤微信官方系统操作消息，保留所有正常对话（含表情、特殊符号）
        :param content: 消息内容
        :return: True为有效对话，False为系统消息/空内容
        """
        if not content or content.strip() == "":
            return False
        # 仅过滤【微信官方系统操作类】消息，剔除宽泛关键词，避免误过滤正常内容
        sys_msg_patterns = [
            r"撤回了一条消息",
            r"发起了群聊",
            r"加入了群聊",
            r"退出了群聊",
            r"修改了群聊名称",
            r"发送了[文件|图片|视频|语音|小程序|红包|转账]",
            r"[语音|视频]通话",
            r"位置共享",
            r"已领取红包",
            r"已转账",
            r"邀请.*加入群聊",
            r"移出了群聊"
        ]
        for pattern in sys_msg_patterns:
            if re.search(pattern, content):
                logger.debug(f"过滤系统消息：{content[:30]}...")
                return False
        # 保留所有正常内容（含表情[xxx]、特殊符号、短句）
        return True

    def _remove_duplicates(self, records: List[Dict]) -> List[Dict]:
        """
        数据去重：基于时间+发送人+内容，保留第一条出现的记录
        :param records: 原始解析记录列表
        :return: 去重后的记录列表
        """
        seen_keys = set()
        unique_records = []
        for record in records:
            # 生成去重键，忽略首尾空格
            key = self.duplicate_key_template.format(
                time=record["time"].strip(),
                sender=record["sender"].strip(),
                content=record["content"].strip()
            )
            if key not in seen_keys:
                seen_keys.add(key)
                unique_records.append(record)
            else:
                logger.debug(f"过滤重复记录：{record['sender']} - {record['content'][:20]}...")
        return unique_records

    def _detect_txt_format(self, txt_content: str) -> str:
        """
        自动检测TXT格式类型
        :param txt_content: TXT原始内容字符串
        :return: txt_with_time / txt_no_time
        """
        # 检测是否包含时间戳标识【】，有则为带时间戳格式
        if re.search(r"【\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", txt_content):
            return "txt_with_time"
        # 检测是否包含 昵称:内容 格式，无时间戳则为极简格式
        elif re.search(r"[^：:\n]+[：:]\s*[\s\S]+(?![\s\n]*$)", txt_content):
            return "txt_no_time"
        else:
            raise ValueError("未识别的TXT格式，非微信标准导出格式")

    def _parse_txt_with_time(self, txt_content: str) -> List[Dict]:
        """
        解析带时间戳的微信TXT格式（原有格式）
        :param txt_content: TXT原始内容字符串
        :return: 原始解析记录列表（未清洗）
        """
        records = []
        matches = self.txt_pattern_with_time.findall(txt_content)
        self.parse_stats["format_type"] = "txt_with_time"  # 先标记格式，后赋值总数

        for idx, match in enumerate(matches):
            try:
                raw_time, _, sender, content = match
                # 基础清洗
                sender = sender.strip()
                content = content.strip().replace("\n", " ").replace("\r", "")
                # 时间标准化
                std_time = self._standardize_time(raw_time)
                # 核心过滤：空发送人/空内容（纯空白字符也过滤）
                if not sender.strip() or not content.strip():
                    continue
                # 构造原始记录
                records.append({
                    "time": std_time,
                    "sender": sender,
                    "content": content,
                    "format": "txt",
                    "is_valid": True
                })
            except Exception as e:
                logger.error(f"TXT带时间戳解析单条记录失败（索引{idx}）：{str(e)[:50]}，跳过该记录")
                continue
        # 关键：total_raw取过滤后的实际记录数，而非初始matches数
        self.parse_stats["total_raw"] = len(records)
        logger.info(f"TXT带时间戳格式解析：匹配到{self.parse_stats['total_raw']}条原始记录")
        return records

    def _parse_txt_no_time(self, txt_content: str) -> List[Dict]:
        """
        解析无时间戳的微信极简格式（你提供的格式）
        :param txt_content: TXT原始内容字符串
        :return: 原始解析记录列表（未清洗）
        """
        records = []
        # 先清洗内容：移除多余空行、首尾空格（避免正则匹配异常）
        clean_txt = re.sub(r"\n{3,}", "\n\n", txt_content).strip()
        matches = self.txt_pattern_no_time.findall(clean_txt)
        self.parse_stats["format_type"] = "txt_no_time"

        for idx, match in enumerate(matches):
            try:
                sender, content = match
                # 深度清洗：移除换行、多余空格、全角空格
                sender = sender.strip().replace("\n", "").replace(" ", "").replace("　", "")
                content = content.strip().replace("\n", " ").replace("\r", "").replace("　", " ")
                # 无时间戳，使用标准化默认时间
                std_time = self._standardize_time("")
                # 过滤空发送人（清洗后）
                if not sender:
                    continue
                # 核心优化：过滤空内容/纯空白字符内容（你的思路+严谨兼容）
                if not content.strip():
                    continue
                # 构造原始记录（数据结构与带时间戳格式完全统一）
                records.append({
                    "time": std_time,
                    "sender": sender,
                    "content": content,
                    "format": "txt",
                    "is_valid": True
                })
            except Exception as e:
                logger.error(f"TXT无时间戳解析单条记录失败（索引{idx}）：{str(e)[:50]}，跳过该记录")
                continue
        # 关键：原始记录数取最终有效构造的records长度，而非初始matches长度
        self.parse_stats["total_raw"] = len(records)
        logger.info(f"TXT无时间戳格式解析：匹配到{self.parse_stats['total_raw']}条原始记录")
        return records

    def _parse_txt(self, txt_content: str) -> List[Dict]:
        """
        TXT统一解析入口：自动检测格式，分发到对应解析函数
        :param txt_content: TXT原始内容字符串
        :return: 原始解析记录列表（未清洗）
        """
        # 自动检测格式
        txt_format = self._detect_txt_format(txt_content)
        if txt_format == "txt_with_time":
            return self._parse_txt_with_time(txt_content)
        else:
            return self._parse_txt_no_time(txt_content)

    def _parse_xml(self, xml_content: str) -> List[Dict]:
        """
        解析微信XML格式聊天记录（兼容微信不同导出版本节点）
        :param xml_content: XML原始内容字符串
        :return: 原始解析记录列表（未清洗）
        """
        records = []
        self.parse_stats["format_type"] = "xml"  # 先标记格式，后赋值总数
        try:
            # 处理XML编码/格式问题
            xml_content = xml_content.strip().encode("utf-8").decode("utf-8", errors="ignore")
            root = ET.fromstring(xml_content)
            # 兼容微信XML节点：msg/Message/ChatRecord/record
            msg_nodes = root.findall(".//msg") or root.findall(".//Message") or \
                        root.findall(".//ChatRecord") or root.findall(".//record")

            for idx, node in enumerate(msg_nodes):
                try:
                    # 提取核心字段（兼容不同节点名）
                    raw_time = node.findtext("time", "") or node.findtext("datetime", "") or ""
                    sender = node.findtext("sender", "") or node.findtext("from", "") or node.findtext("username",
                                                                                                       "") or ""
                    content = node.findtext("content", "") or node.findtext("text", "") or ""
                    # 基础清洗
                    sender = sender.strip()
                    content = content.strip().replace("\n", " ").replace("\r", "")
                    # 时间标准化（支持时间戳/原始时间/空时间）
                    std_time = self._standardize_time(raw_time)
                    # 核心过滤：空发送人/空内容（纯空白字符也过滤），和TXT逻辑完全一致
                    if not sender.strip() or not content.strip():
                        continue
                    # 构造原始记录
                    records.append({
                        "time": std_time,
                        "sender": sender,
                        "content": content,
                        "format": "xml",
                        "is_valid": True
                    })
                except Exception as e:
                    logger.error(f"XML解析单条记录失败（索引{idx}）：{str(e)[:50]}，跳过该记录")
                    continue
        except ET.ParseError as e:
            logger.error(f"XML格式非法，解析失败：{str(e)[:50]}")
        except Exception as e:
            logger.error(f"XML解析异常：{str(e)[:50]}")
        # 关键：total_raw取过滤后的实际记录数，而非初始msg_nodes数
        self.parse_stats["total_raw"] = len(records)
        logger.info(f"XML格式解析：匹配到{self.parse_stats['total_raw']}条原始记录")
        return records

    def _clean_records(self, raw_records: List[Dict]) -> List[Dict]:
        """
        【核心升级】数据清洗主流程：系统消息过滤 → 无效内容过滤 → 去重 → 二次校验
        :param raw_records: 原始解析记录列表
        :return: 清洗后的有效记录列表
        """
        # 第一步：过滤系统消息
        filter_sys_records = [r for r in raw_records if self._filter_system_message(r["content"])]
        # 第二步：过滤无效内容（纯媒体/纯表情/空内容，新增核心步骤）
        filter_invalid_records = [r for r in filter_sys_records if self._filter_invalid_content(r["content"])]
        # 第三步：去重
        clean_records = self._remove_duplicates(filter_invalid_records)
        # 第四步：二次校验有效标识
        clean_records = [r for r in clean_records if r.get("is_valid", False)]

        # 更新统计
        self.parse_stats["total_clean"] = len(clean_records)
        self.parse_stats["filter_count"] = self.parse_stats["total_raw"] - self.parse_stats["total_clean"]
        # 计算解析准确率（避免除零错误）
        if self.parse_stats["total_raw"] > 0:
            self.parse_stats["accuracy"] = round((self.parse_stats["total_clean"] / self.parse_stats["total_raw"]) * 100, 2)
        else:
            self.parse_stats["accuracy"] = 0.0
        logger.info(f"数据清洗完成：原始{self.parse_stats['total_raw']}条 → 有效{self.parse_stats['total_clean']}条，准确率{self.parse_stats['accuracy']}%")
        return clean_records

    def parse(self, content: str, format_type: str, use_cache: bool = True) -> Dict:
        """
        对外统一解析接口：整合「缓存→解析→清洗→统计」全流程
        :param content: 聊天记录原始内容字符串
        :param format_type: 格式类型，可选txt/xml（需在settings.PARSE_SUPPORT_FORMATS中）
        :param use_cache: 是否使用LRU缓存，默认True
        :return: 标准化解析结果（含记录、统计、状态）
        """
        # 初始化返回结果
        result = {
            "code": 200,
            "msg": "解析成功",
            "data": {
                "records": [],
                "stats": {}
            }
        }
        # 重置解析统计（每次解析重置默认时间，保证无时间戳记录时间为当前解析时间）
        self.default_time = datetime.now().strftime(settings.PARSE_TIME_FORMAT)
        self.parse_stats = {
            "total_raw": 0,
            "total_clean": 0,
            "filter_count": 0,
            "accuracy": 0.0,
            "parse_time": 0.0,
            "format_type": ""
        }
        start_time = time.time()

        try:
            # 1. 入参校验
            if format_type not in settings.PARSE_SUPPORT_FORMATS:
                raise ValueError(f"不支持的格式类型：{format_type}，仅支持{settings.PARSE_SUPPORT_FORMATS}")
            if not content or content.strip() == "":
                raise ValueError("原始内容为空，无法解析")

            # 2. 缓存逻辑：生成key → 检查缓存 → 命中则直接返回
            cache_key = generate_content_key(content)
            if use_cache and cache_key and global_cache.get(cache_key):
                result = global_cache.get(cache_key)
                result["data"]["stats"]["parse_time"] = round(time.time() - start_time, 3)
                logger.info(f"解析完成（缓存命中）：{result['data']['stats']['accuracy']}%准确率，耗时{result['data']['stats']['parse_time']}s")
                return result

            # 3. 按格式解析原始记录
            raw_records = []
            if format_type == "txt":
                raw_records = self._parse_txt(content)
            else:
                raw_records = self._parse_xml(content)

            # 4. 数据清洗（升级后）
            clean_records = self._clean_records(raw_records)

            # 5. 构造结果
            self.parse_stats["parse_time"] = round(time.time() - start_time, 3)
            result["data"]["records"] = clean_records
            result["data"]["stats"] = self.parse_stats

            # 6. 缓存逻辑：未命中则设置缓存
            if use_cache and cache_key:
                global_cache.set(cache_key, result)

            logger.info(f"解析完成（缓存未命中）：{self.parse_stats['accuracy']}%准确率，耗时{self.parse_stats['parse_time']}s")
            return result

        except ValueError as e:
            result["code"] = 400
            result["msg"] = str(e)
            logger.warning(f"解析参数错误：{str(e)}")
        except Exception as e:
            result["code"] = 500
            result["msg"] = f"解析失败：{str(e)[:50]}"
            logger.error(f"解析异常：{str(e)}", exc_info=True)
        finally:
            # 保证统计信息始终返回
            if not result["data"]["stats"]:
                result["data"]["stats"] = self.parse_stats
            result["data"]["stats"]["parse_time"] = round(time.time() - start_time, 3)

        return result

# 全局解析器实例（单例，供外部调用）
wechat_chat_parser = WeChatChatParser()