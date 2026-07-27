from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.services.data_store import data_store
from app.services.performance_monitor import performance_monitor


router = APIRouter()


class PdfExportMetric(BaseModel):
    elapsed_ms: Optional[float] = Field(default=None, description="PDF 导出耗时，单位毫秒")
    elapsed_s: Optional[float] = Field(default=None, description="PDF 导出耗时，单位秒")


class WebSocketLatencyMetric(BaseModel):
    elapsed_ms: float = Field(description="后端消息时间戳与前端接收时间差，单位毫秒")


@router.get("/thesis-table", response_model=ResponseModel)
async def get_thesis_performance_table(
    printToConsole: bool = True,
    current_user: dict = Depends(get_current_active_user),
):
    """获取并打印论文“系统性能测试记录模板”对应的后端采集数据。"""
    db_write_stats = data_store.get_write_stats()
    table = performance_monitor.build_thesis_table(db_write_stats)
    if printToConsole:
        performance_monitor.print_thesis_table(db_write_stats)
    return ResponseModel(data=table)


@router.post("/pdf-export", response_model=ResponseModel)
async def record_pdf_export_metric(
    metric: PdfExportMetric,
    current_user: dict = Depends(get_current_active_user),
):
    """记录前端 PDF 导出耗时，供论文性能测试表使用。"""
    if metric.elapsed_ms is not None:
        elapsed_ms = float(metric.elapsed_ms)
    elif metric.elapsed_s is not None:
        elapsed_ms = float(metric.elapsed_s) * 1000
    else:
        return ResponseModel(code=400, message="请提供 elapsed_ms 或 elapsed_s")

    performance_monitor.record_pdf_export(elapsed_ms / 1000)
    user = (current_user or {}).get("username") or (current_user or {}).get("sub") or "unknown"
    print(
        f"[PDF导出性能] user={user} "
        f"elapsed={round(elapsed_ms, 2)} ms "
        f"({round(elapsed_ms / 1000, 3)} s)"
    )
    return ResponseModel(data={"pdf_export_elapsed_s": round(elapsed_ms / 1000, 2)})


@router.post("/websocket-latency", response_model=ResponseModel)
async def record_websocket_latency_metric(
    metric: WebSocketLatencyMetric,
    current_user: dict = Depends(get_current_active_user),
):
    """记录实时推送延迟，供论文性能测试表使用。"""
    performance_monitor.record_websocket_latency(metric.elapsed_ms)
    return ResponseModel(data={"websocket_latency_ms": round(metric.elapsed_ms, 2)})
