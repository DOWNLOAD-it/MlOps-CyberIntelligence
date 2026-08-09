select
  1 as id,
  'demo_event' as event_name,
  '2026-01-01 00:00:00'::timestamp as event_time,
  '192.168.0.1' as source_ip,
  '10.0.0.1' as destination_ip,
  80 as destination_port,
  0 as is_attack
