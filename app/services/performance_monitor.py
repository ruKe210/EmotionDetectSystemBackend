"""
论文性能测试指标采集器

用于汇总“系统性能测试记录模板”中的后端可观测数据。
"""
from collections import defaultdict, deque
from datetime import datetime
import threading
from typing import Callable, Deque, Dict, List, Optional


class PerformanceMonitor:
    """集中记录推理、推送、报表和导出相关性能数据。"""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.Lock()
        self._inference_times: Deque[float] = deque(maxlen=1000)
        self._per_camera_inference: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=2000)
        )
        self._fps_values: Deque[float] = deque(maxlen=600)
        self._websocket_push_times: Deque[float] = deque(maxlen=1000)
        self._per_camera_ws_push: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=2000)
        )
        self._websocket_latencies: Deque[float] = deque(maxlen=1000)
        self._link_attempts: Dict[str, int] = defaultdict(int)
        self._link_success: Dict[str, int] = defaultdict(int)
        self._report_response_times: Deque[float] = deque(maxlen=1000)
        self._pdf_export_times: Deque[float] = deque(maxlen=200)
        self._last_updated: Optional[str] = None
        self._printer_thread: Optional[threading.Thread] = None
        self._printer_stop_event = threading.Event()

    def _touch(self):
        self._last_updated = datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _avg(values: Deque[float]) -> Optional[float]:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _latest(values: Deque[float]) -> Optional[float]:
        if not values:
            return None
        return round(values[-1], 2)

    def record_inference(
        self,
        inference_time_ms: float,
        fps: Optional[float] = None,
        camera_id: Optional[str] = None,
    ):
        with self._lock:
            self._inference_times.append(float(inference_time_ms))
            if camera_id:
                self._per_camera_inference[camera_id].append(float(inference_time_ms))
            if fps is not None:
                self._fps_values.append(float(fps))
            self._touch()

    def record_fps(self, fps: float):
        with self._lock:
            self._fps_values.append(float(fps))
            self._touch()

    def record_websocket_push(
        self, elapsed_ms: float, camera_id: Optional[str] = None
    ):
        with self._lock:
            self._websocket_push_times.append(float(elapsed_ms))
            if camera_id:
                self._per_camera_ws_push[camera_id].append(float(elapsed_ms))
            self._touch()

    def record_camera_cycle(self, camera_id: str, success: bool):
        """单路摄像头一次采集—推理周期：success 表示读到帧并完成推理与后续链路。"""
        with self._lock:
            self._link_attempts[camera_id] += 1
            if success:
                self._link_success[camera_id] += 1

    def record_websocket_latency(self, elapsed_ms: float):
        with self._lock:
            self._websocket_latencies.append(float(elapsed_ms))
            self._touch()

    def record_report_response(self, elapsed_ms: float):
        with self._lock:
            self._report_response_times.append(float(elapsed_ms))
            self._touch()

    def record_pdf_export(self, elapsed_s: float):
        with self._lock:
            self._pdf_export_times.append(float(elapsed_s))
            self._touch()

    def get_summary(self, db_write_stats: Optional[Dict] = None) -> Dict:
        with self._lock:
            summary = {
                "last_updated": self._last_updated,
                "inference": {
                    "avg_ms": self._avg(self._inference_times),
                    "latest_ms": self._latest(self._inference_times),
                    "samples": len(self._inference_times),
                },
                "fps": {
                    "avg": self._avg(self._fps_values),
                    "latest": self._latest(self._fps_values),
                    "samples": len(self._fps_values),
                },
                "websocket_push": {
                    "avg_ms": self._avg(self._websocket_push_times),
                    "latest_ms": self._latest(self._websocket_push_times),
                    "samples": len(self._websocket_push_times),
                    "note": "后端 WebSocket send_text 发送耗时",
                },
                "websocket_latency": {
                    "avg_ms": self._avg(self._websocket_latencies),
                    "latest_ms": self._latest(self._websocket_latencies),
                    "samples": len(self._websocket_latencies),
                    "note": "由前端根据后端消息时间戳与接收时间差上报",
                },
                "report_api": {
                    "avg_ms": self._avg(self._report_response_times),
                    "latest_ms": self._latest(self._report_response_times),
                    "samples": len(self._report_response_times),
                },
                "pdf_export": {
                    "avg_s": self._avg(self._pdf_export_times),
                    "latest_s": self._latest(self._pdf_export_times),
                    "samples": len(self._pdf_export_times),
                    "note": "PDF 由前端生成，需前端导出完成后调用上报接口",
                },
            }
        summary["database_write"] = db_write_stats or {}
        return summary

    def build_thesis_table(self, db_write_stats: Optional[Dict] = None) -> Dict:
        summary = self.get_summary(db_write_stats)
        db_stats = summary.get("database_write", {})
        failed = int(db_stats.get("failed_batches", 0) or 0)
        queued = int(db_stats.get("queued_records", 0) or 0)
        written = int(db_stats.get("written_records", 0) or 0)
        dropped = int(db_stats.get("dropped_records", 0) or 0)
        db_status = "正常" if failed == 0 and dropped == 0 else f"异常：失败批次 {failed}，丢弃 {dropped} 条"
        inference_result = self._format_value(summary["inference"]["avg_ms"], "ms")
        fps_result = self._format_fps(summary["fps"]["avg"])
        websocket_result = self._format_value(summary["websocket_latency"]["avg_ms"], "ms")
        report_result = self._format_value(summary["report_api"]["avg_ms"], "ms")
        pdf_result = self._format_value(summary["pdf_export"]["avg_s"], "s")

        rows = [
            {
                "编号": 1,
                "测试指标": "单帧平均推理耗时",
                "测试方法": "每 10 秒统计一次当前平均值",
                "结果": inference_result,
            },
            {
                "编号": 2,
                "测试指标": "实时识别帧率",
                "测试方法": "记录后端统计字段 fps 的平均值",
                "结果": fps_result,
            },
            {
                "编号": 3,
                "测试指标": "实时推送延迟",
                "测试方法": "记录后端时间戳与前端接收时间差",
                "结果": websocket_result,
            },
            {
                "编号": 4,
                "测试指标": "报表接口响应时间",
                "测试方法": "请求日报、周报、月报接口并取平均值",
                "结果": report_result,
            },
            {
                "编号": 5,
                "测试指标": "PDF 导出耗时",
                "测试方法": "从点击导出到文件生成完成计时",
                "结果": pdf_result,
            },
            {
                "编号": 6,
                "测试指标": "数据库写入稳定性",
                "测试方法": "连续识别期间观察写入失败数",
                "结果": f"{db_status}；写入失败 {failed} 批，已入库 {written} 条，入队 {queued} 条",
            },
        ]
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "rows": rows,
            "raw": summary,
        }

    @staticmethod
    def _format_value(value: Optional[float], unit: str) -> str:
        if value is None:
            return "待采集"
        return f"{value} {unit}"

    @staticmethod
    def _format_fps(value: Optional[float]) -> str:
        if value is None:
            return "待采集"
        return f"{value} FPS，正常"

    def print_thesis_table(self, db_write_stats: Optional[Dict] = None):
        table = self.build_thesis_table(db_write_stats)
        print("\n" + "=" * 100)
        print("表 6.5 系统性能测试结果")
        print("=" * 100)
        print("编号\t测试指标\t\t测试方法\t\t\t\t结果")
        print("-" * 100)
        for row in table["rows"]:
            print(
                f"{row['编号']}\t{row['测试指标']}\t{row['测试方法']}\t{row['结果']}"
            )
        print("=" * 100 + "\n")

    def print_camera_link_table(self, camera_ids: List[str]):
        """按摄像头打印：本周期内平均推理耗时、平均推送耗时（send 段）、链路成功率。"""
        if not camera_ids:
            print("[实时链路] 当前无活跃摄像头\n")
            return

        rows = self.snapshot_per_camera_metrics(camera_ids)
        print("=" * 100)
        print("实时链路（按摄像头，统计区间为上次打印至今，约 10 s）")
        print("推送(ms)：人脸 face 频道 WebSocket 单次广播 send 段；无订阅客户端时多为 —")
        print("=" * 100)
        print(
            f"{'摄像头 ID':<28}{'平均推理(ms)':<16}{'平均推送(ms)':<16}{'链路成功次数/尝试':<22}{'链路成功率'}"
        )
        print("-" * 100)
        for r in rows:
            print(
                f"{r['camera_id']:<28}"
                f"{r['inference_ms']:<16}"
                f"{r['push_ms']:<16}"
                f"{r['link_counts']:<22}"
                f"{r['link_rate']}"
            )
        print("=" * 100 + "\n")

    def snapshot_per_camera_metrics(self, camera_ids: List[str]) -> List[Dict]:
        with self._lock:
            out: List[Dict] = []
            for cid in camera_ids:
                inf_q = self._per_camera_inference.get(cid)
                push_q = self._per_camera_ws_push.get(cid)

                if inf_q:
                    inf_avg = round(sum(inf_q) / len(inf_q), 2)
                    inf_q.clear()
                    inf_str = str(inf_avg)
                else:
                    inf_str = "—"

                if push_q:
                    push_avg = round(sum(push_q) / len(push_q), 2)
                    push_q.clear()
                    push_str = str(push_avg)
                else:
                    push_str = "—"

                att = self._link_attempts.pop(cid, 0)
                suc = self._link_success.pop(cid, 0)
                if att:
                    rate = round(100.0 * suc / att, 2)
                    rate_str = f"{rate}%"
                    cnt_str = f"{suc}/{att}"
                else:
                    rate_str = "—"
                    cnt_str = "0/0"

                out.append(
                    {
                        "camera_id": cid,
                        "inference_ms": inf_str,
                        "push_ms": push_str,
                        "link_counts": cnt_str,
                        "link_rate": rate_str,
                    }
                )
            return out

    def start_periodic_print(
        self,
        get_db_write_stats,
        interval_seconds: int = 10,
        get_camera_ids: Optional[Callable[[], List[str]]] = None,
    ):
        """启动定时打印线程，每隔固定时间输出论文性能测试表与分摄像头实时链路表。"""
        if self._printer_thread and self._printer_thread.is_alive():
            return

        self._printer_stop_event.clear()

        def _loop_while():
            while not self._printer_stop_event.wait(interval_seconds):
                try:
                    self.print_thesis_table(get_db_write_stats())
                except Exception as exc:
                    print(f"[性能测试] 定时打印失败: {exc}")
                if get_camera_ids:
                    try:
                        ids = get_camera_ids()
                        self.print_camera_link_table(ids)
                    except Exception as exc:
                        print(f"[实时链路] 定时打印失败: {exc}")

        self._printer_thread = threading.Thread(target=_loop_while, daemon=True)
        self._printer_thread.start()
        print(
            f"[性能测试] 已启动定时打印（论文性能表 + 分摄像头实时链路），每 {interval_seconds} 秒一次"
        )

    def stop_periodic_print(self):
        """停止定时打印线程。"""
        self._printer_stop_event.set()
        if self._printer_thread and self._printer_thread.is_alive():
            self._printer_thread.join(timeout=1)
        self._printer_thread = None


performance_monitor = PerformanceMonitor()
