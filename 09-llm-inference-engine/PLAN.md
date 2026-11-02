# Stage 9: Small LLM inference engine

## Objective

Build a small educational inference engine to understand LLM internals: load existing weights, implement a transformer forward pass, generate tokens, and measure the effects of KV caching. Demonstrate numerical correctness before pursuing speed.

## Entry requirements

Python, tensor shapes and operations, basic linear algebra, and the request/token concepts from stage 1. Recommended learning slot: after stages 1-2. Folder numbering is portfolio organization, not a requirement to finish stages 3-8 first. Stage 9 is a separate fundamentals project and is not required to serve the flagship application.

## What to design

- Choose one small decoder-only model architecture and a checkpoint that fits available hardware. Record architecture/configuration, tokenizer, weight format, license, revision, dtype, and device. Do not assume a GPU is available.
- Use PyTorch tensor operations to implement embeddings, causal self-attention, the architecture's positional encoding, normalization, feed-forward blocks, residual paths, and output projection. Match the chosen architecture rather than combining incompatible components.
- Reuse a compatible tokenizer initially, while explaining token IDs, special tokens, encoding/decoding, and context limits. Implementing a tokenizer is optional.
- Design a weight loader with explicit parameter-name/shape mapping and tied-weight handling when applicable. Keep reference-library inference outside the custom execution path.
- Implement prefill and autoregressive decoding with EOS/max-token stopping, greedy decoding, temperature, top-k, and top-p sampling. Define seeded reproducibility and invalid-input behavior.
- Implement a per-request KV cache with correct positions, causal masking, context bounds, cache reset, and no state leakage between requests.
- Define a reference-comparison harness and benchmarks for time to first token, decode tokens/second, and memory. Separate model loading, tokenization, prefill, and decode measurements.

## Build sequence

1. Inspect available hardware and select one small model/checkpoint with accessible weights. Record the choice and a minimal runnable configuration.
2. Document tensor shapes through one transformer block and build the uncached forward pass with weight loading.
3. Compare intermediate activations and final logits against a reference implementation in evaluation mode; resolve mismatches before adding optimizations.
4. Implement bounded generation and sampling, with deterministic greedy fixtures and controlled random seeds where supported.
5. Add KV caching and compare cached versus uncached next-token logits over multi-token sequences and separate requests.
6. Benchmark both paths under identical workloads and report warm-up, repeated runs, prompt/output lengths, dtype, hardware, and measurement limitations.
7. Write an internals walkthrough and failure/debugging case study; refresh the stage 8 portfolio index with verified evidence.

## Acceptance criteria

- [ ] The custom engine loads the selected checkpoint and runs its own tensor-based forward/generation path, without delegating that path to a reference model's forward or generate method.
- [ ] Logits match the reference within documented dtype/device-appropriate tolerances on a fixed prompt set. Record maximum/aggregate error and investigate mismatches; fluent text alone is not correctness evidence.
- [ ] Tests cover causal masking, position handling, tensor shapes, EOS/max-token stopping, context overflow, and invalid sampling configuration.
- [ ] Cached and uncached decoding agree within the declared tolerance across several prompt/output lengths; independent requests cannot reuse stale cache state.
- [ ] Greedy decoding is reproducible in the documented environment. Sampling tests check valid distributions and filtering behavior without assuming identical outputs across different hardware.
- [ ] A reproducible benchmark compares latency, throughput, and memory with caching on/off, including synchronization for accelerator timing when applicable. Report results honestly even if caching is slower on a tiny workload.
- [ ] A walkthrough explains the forward pass, prefill/decode distinction, KV-cache memory tradeoff, and known implementation limitations.

## Portfolio evidence to collect

Architecture/configuration manifest, tensor-shape walkthrough, weight-mapping notes, reference-parity report, cache correctness tests, benchmark commands/results, and a short CLI demonstration. Save reports in this folder's eventual `evidence/` directory and link them from [progress](../docs/PROGRESS.md).

## Handoff to the next stage

A standalone inference project proving model-level understanding, plus correctness/performance fixtures that stage 10 may evaluate through an optional adapter. Stage 10 does not depend on stage 9 being a production inference server.

## Scope boundary

No model training, custom autograd engine, CUDA kernels, multi-GPU execution, continuous batching, quantization, or production serving is required. Those are optional extensions after correctness and measurement. This project should not delay the flagship through attempts to reproduce a full production inference platform.

## Context

Read [master plan](../MASTER_PLAN.md), [root memory](../memory.md), and [stage memory](memory.md). All behavior above is planned, not implemented.
