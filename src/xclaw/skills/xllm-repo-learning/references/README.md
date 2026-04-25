# xLLM Reference Navigator

This directory is intentionally topic-sliced. For agent use, load the smallest set that answers the question, then verify high-risk claims against current xLLM source.

## Read Order

- Broad architecture: `0-overview.md` -> `1-structure.md`.
- Data objects: `10-request.md` -> `5-batch.md` -> `11-scheduler.md`.
- Cache path: `2-prefix_cache.md` -> `8-kv_cache.md` -> `4-pd_disaggregate.md`.
- Execution optimization: choose one of `3-schedule_overlap.md`, `6-eplb.md`, `7-graph.md`, `9-parallel_state.md`, `12-xtensor.md`.

## Question Router

| User intent | Primary notes | Usually verify in source |
| --- | --- | --- |
| Startup, flags, backend, model capability | `0-overview.md`, `1-structure.md` | `xllm/xllm.cpp`, `xllm/core/distributed_runtime/master.cpp`, `xllm/core/common/global_flags.cpp`, `xllm/core/common/options.h` |
| API request path and streaming | `1-structure.md`, `10-request.md` | `xllm/api_service/api_service.cpp`, `xllm/api_service/chat_service_impl.cpp`, `xllm/core/distributed_runtime/llm_master.cpp` |
| Request / Sequence / SequencesGroup semantics | `10-request.md` | `xllm/core/framework/request/request.h`, `xllm/core/framework/request/sequence.h`, `xllm/core/framework/request/sequences_group.h` |
| Scheduler selection and scheduling policy | `11-scheduler.md`, `5-batch.md` | `xllm/core/scheduler/scheduler_factory.cpp`, `xllm/core/scheduler/continuous_scheduler.cpp`, `xllm/core/scheduler/chunked_prefill_scheduler.cpp` |
| Batch construction and output writeback | `5-batch.md`, `10-request.md` | `xllm/core/framework/batch/batch.h`, `xllm/core/framework/batch/batch_factory.cpp`, `xllm/core/framework/batch/batch_input_builder.cpp` |
| Prefix cache behavior | `2-prefix_cache.md`, `8-kv_cache.md` | `xllm/core/framework/block/block_manager_pool.cpp`, `xllm/core/framework/prefix_cache/prefix_cache.cpp`, `xllm/core/framework/request/sequence_kv_state.cpp` |
| KV cache shape, host/store, PD transfer | `8-kv_cache.md`, `4-pd_disaggregate.md` | `xllm/core/framework/kv_cache/kv_cache_shape.cpp`, `xllm/core/framework/kv_cache_transfer/kv_cache_transfer.cpp`, `xllm/core/framework/kv_cache_transfer/kv_cache_store.cpp` |
| PD disaggregation | `4-pd_disaggregate.md`, `11-scheduler.md` | `xllm/core/scheduler/disagg_pd_scheduler.cpp`, `xllm/core/distributed_runtime/disagg_pd_service_impl.cpp`, `xllm/core/runtime/llm_worker_impl.cpp` |
| Schedule overlap | `3-schedule_overlap.md`, `11-scheduler.md` | `xllm/core/distributed_runtime/llm_engine.cpp`, `xllm/core/runtime/llm_worker_impl.cpp`, `xllm/core/runtime/worker_impl.cpp` |
| EPLB / MoE load balancing | `6-eplb.md`, `9-parallel_state.md` | `xllm/core/framework/eplb/eplb_manager.cpp`, `xllm/core/runtime/llm_worker_impl.cpp`, `xllm/core/framework/eplb/expert_buffer_manager.cpp` |
| CUDA/ACL graph mode | `7-graph.md` | `xllm/core/runtime/cuda_graph_executor_impl.cpp`, `xllm/core/runtime/acl_graph_executor_impl.cpp`, `xllm/core/runtime/worker_impl.cpp` |
| Parallel topology and process groups | `9-parallel_state.md` | `xllm/core/framework/parallel_state/parallel_args.h`, `xllm/core/framework/parallel_state/collective_communicator.cpp`, `xllm/core/distributed_runtime/worker_server.cpp` |
| xTensor, rolling load, weight/KV paging | `12-xtensor.md`, `8-kv_cache.md` | `xllm/core/framework/xtensor/xtensor_allocator.cpp`, `xllm/core/framework/xtensor/phy_page_pool.cpp`, `xllm/core/layers/npu/loader/base_manual_loader.cpp` |

## Minimal Context Bundles

- "How does xLLM work end to end?": `0-overview.md` + `1-structure.md`.
- "Where does an OpenAI chat request go?": `1-structure.md` + `10-request.md`.
- "Why did this request enter this batch?": `10-request.md` + `5-batch.md` + `11-scheduler.md`.
- "Why are KV blocks missing, reused, or moved?": `2-prefix_cache.md` + `8-kv_cache.md`.
- "Why does PD behave differently from normal decode?": `4-pd_disaggregate.md` + `11-scheduler.md`.
- "Why does an optimization hook into execution?": choose the optimization topic, then verify in `xllm/core/runtime/worker_impl.cpp` and `xllm/core/distributed_runtime/llm_engine.cpp`.

## Source Verification Rules

- Treat notes as a map, not an authority. If code and notes differ, trust code and mention the drift.
- Always re-check gflags/defaults and option propagation before answering config questions.
- Always re-check scheduler factory ordering before answering scheduler-selection questions.
- Always re-check backend guards (`USE_NPU`, `USE_CUDA`, `USE_MLU`) before generalizing execution behavior.
- For path-sensitive topics, run `python3 ../scripts/check_xllm_refs.py` from this directory or `python3 scripts/check_xllm_refs.py` from the skill root.

## Maintenance Checklist

When updating any topic note:

1. Update this navigator if the topic boundary or key source files changed.
2. Run `python3 scripts/check_xllm_refs.py` from the skill root.
3. If a stale phrase caused the update, add it to `scripts/check_xllm_refs.py` as a `DEFAULT_STALE_PATTERNS` entry.
4. Keep new notes source-grounded: include classes/functions/paths, not only conceptual summaries.
