from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class NetworkRecord(BaseModel):
    destination_port: Optional[float] = 0.0
    flow_duration: Optional[float] = 0.0
    total_fwd_packets: Optional[float] = 0.0
    total_backward_packets: Optional[float] = 0.0
    total_length_of_fwd_packets: Optional[float] = 0.0
    total_length_of_bwd_packets: Optional[float] = 0.0
    fwd_packet_length_max: Optional[float] = 0.0
    fwd_packet_length_min: Optional[float] = 0.0
    fwd_packet_length_mean: Optional[float] = 0.0
    fwd_packet_length_std: Optional[float] = 0.0
    bwd_packet_length_max: Optional[float] = 0.0
    bwd_packet_length_min: Optional[float] = 0.0
    bwd_packet_length_mean: Optional[float] = 0.0
    bwd_packet_length_std: Optional[float] = 0.0
    flow_bytes_s: Optional[float] = 0.0
    flow_packets_s: Optional[float] = 0.0
    flow_iat_mean: Optional[float] = 0.0
    flow_iat_std: Optional[float] = 0.0
    flow_iat_max: Optional[float] = 0.0
    flow_iat_min: Optional[float] = 0.0
    fwd_iat_total: Optional[float] = 0.0
    fwd_iat_mean: Optional[float] = 0.0
    fwd_iat_std: Optional[float] = 0.0
    fwd_iat_max: Optional[float] = 0.0
    fwd_iat_min: Optional[float] = 0.0
    bwd_iat_total: Optional[float] = 0.0
    bwd_iat_mean: Optional[float] = 0.0
    bwd_iat_std: Optional[float] = 0.0
    bwd_iat_max: Optional[float] = 0.0
    bwd_iat_min: Optional[float] = 0.0
    fwd_psh_flags: Optional[float] = 0.0
    bwd_psh_flags: Optional[float] = 0.0
    fwd_urg_flags: Optional[float] = 0.0
    bwd_urg_flags: Optional[float] = 0.0
    fwd_header_length: Optional[float] = 0.0
    bwd_header_length: Optional[float] = 0.0
    fwd_packets_s: Optional[float] = 0.0
    bwd_packets_s: Optional[float] = 0.0
    min_packet_length: Optional[float] = 0.0
    max_packet_length: Optional[float] = 0.0
    packet_length_mean: Optional[float] = 0.0
    packet_length_std: Optional[float] = 0.0
    packet_length_variance: Optional[float] = 0.0
    fin_flag_count: Optional[float] = 0.0
    syn_flag_count: Optional[float] = 0.0
    rst_flag_count: Optional[float] = 0.0
    psh_flag_count: Optional[float] = 0.0
    ack_flag_count: Optional[float] = 0.0
    urg_flag_count: Optional[float] = 0.0
    cwe_flag_count: Optional[float] = 0.0
    ece_flag_count: Optional[float] = 0.0
    down_up_ratio: Optional[float] = 0.0
    average_packet_size: Optional[float] = 0.0
    avg_fwd_segment_size: Optional[float] = 0.0
    avg_bwd_segment_size: Optional[float] = 0.0
    fwd_header_length_1: Optional[float] = 0.0
    fwd_avg_bytes_bulk: Optional[float] = 0.0
    fwd_avg_packets_bulk: Optional[float] = 0.0
    fwd_avg_bulk_rate: Optional[float] = 0.0
    bwd_avg_bytes_bulk: Optional[float] = 0.0
    bwd_avg_packets_bulk: Optional[float] = 0.0
    bwd_avg_bulk_rate: Optional[float] = 0.0
    subflow_fwd_packets: Optional[float] = 0.0
    subflow_fwd_bytes: Optional[float] = 0.0
    subflow_bwd_packets: Optional[float] = 0.0
    subflow_bwd_bytes: Optional[float] = 0.0
    init_win_bytes_forward: Optional[float] = 0.0
    init_win_bytes_backward: Optional[float] = 0.0
    act_data_pkt_fwd: Optional[float] = 0.0
    min_seg_size_forward: Optional[float] = 0.0
    active_mean: Optional[float] = 0.0
    active_std: Optional[float] = 0.0
    active_max: Optional[float] = 0.0
    active_min: Optional[float] = 0.0
    idle_mean: Optional[float] = 0.0
    idle_std: Optional[float] = 0.0
    idle_max: Optional[float] = 0.0
    idle_min: Optional[float] = 0.0


class PredictionResponse(BaseModel):
    is_attack: bool
    confidence: float
    attack_type: str


class RealtimeAlert(BaseModel):
    id: int
    timestamp: str
    attack_type: Optional[str] = None
    destination_port: Optional[int] = None
    flow_duration: Optional[int] = None
    confidence: Optional[float] = None


class RealtimeLatestResponse(BaseModel):
    alerts: List[RealtimeAlert]
    last_id: int


class RealtimeStats(BaseModel):
    rate_per_minute: float
    total_last_hour: int
    attacks_last_hour: int
    benign_last_hour: int
    top_attack_type: str
    avg_confidence_last_hour: float
    by_type_last_hour: Dict[str, int]
    by_minute: List[Dict[str, Any]]
