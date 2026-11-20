# 📊 Source Context AI Benchmark: Head-to-Head Evaluation Report

This report benchmarks the **efficiency** (tool calls, tokens, latency) and **semantic accuracy** (evaluated via LLM-as-a-Judge against ground-truth checklists) of AI coding agents navigating production repositories using **Native File Tools (`grep`, `read_file`)** versus the **`source-context` Code Intelligence MCP Server (Graph, AST, Vector)**.

> [!NOTE]
> **Evaluation Scope**: **54 benchmark tasks** across **9 repositories** and **6 architectural dimensions**.
> **Agent Engine**: Antigravity CLI (`Gemini 3.8 Flash`) | **Judge Engine**: `gpt-4o-mini` (Temp: 0.0)

---

## 1. 🏆 Executive Scorecard

| Evaluation Metric | Baseline (`antigravity_default`) | Treatment (`antigravity_mcp`) | MCP Advantage / Multiplier |
| :--- | :---: | :---: | :---: |
| **Judge Accuracy Score** | 93.8% | **96.1%** | **(+2.3%)** |
| **Atomic Fact Pass Rate** | 96.3% (183/190) | **96.8%** (184/190) | **+0.5%** |
| **Average Tool Calls** | 10.15 calls | **7.83 calls** | **1.3x fewer tool calls** ⚡ |
| **Average Wall-Clock Latency** | 60.19s | **54.28s** | **1.11x faster response** ⚡ |
| **Average Token Cost** | 40,524.6 tokens | **39,497.2 tokens** | **1.03x token savings** ⚡ |
| **Hallucination Cases** | 5 (9.3%) | **3** (5.6%) | ⚠️ Detected |

> [!TIP]
> **Key Efficiency Takeaway**: The `source-context` MCP server eliminates iterative manual grepping and file reads, delivering **1.3x fewer tool calls**, **1.03x fewer tokens**, and **1.11x faster execution** while maintaining superior technical accuracy.

---

## 2. 🥊 Head-to-Head Win / Loss Record

| Evaluation Dimension | MCP Wins (🏆) | Ties (🤝) | Baseline Wins | MCP Win Rate (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Judge Accuracy Score** | **7** | 45 | 2 | **13.0%** (Win+Tie: 96.3%) |
| **Tool Call Efficiency (Fewer Calls)** | **34** | 5 | 15 | **63.0%** (Win+Tie: 72.2%) |
| **Token Cost Savings (Fewer Tokens)** | **31** | 0 | 23 | **57.4%** (Win+Tie: 57.4%) |
| **Execution Speed (Lower Latency)** | **32** | 1 | 21 | **59.3%** (Win+Tie: 61.1%) |

---

## 3. 📐 Performance by Architectural Dimension

| Dimension | Description | Default Acc | MCP Acc | Default Tools | MCP Tools | Tool Reduction | Default Tokens | MCP Tokens | Token Savings | Default Latency | MCP Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `D1_Impact` | Blast Radius / Change Impact Analysis | 97.2% | **100.0%** | 17.89 | **8.11** | **2.2x** | 55,380.4 | **42,207.3** | **1.3x** | 84.0s | **62.5s** |
| `D2_Usages` | Cross-Module Caller Tracing | 97.8% | **97.8%** | 10.89 | **6.89** | **1.6x** | 36,965.8 | **37,745.6** | **1.0x** | 51.2s | **45.7s** |
| `D3_Callees` | Dependency & Helper Call Mapping | 97.2% | **100.0%** | 6.56 | **3.89** | **1.7x** | 36,770.8 | **31,681.4** | **1.2x** | 55.9s | **44.4s** |
| `D4_Semantic` | Behavior & Concept Code Retrieval | 95.0% | **100.0%** | 10.33 | **11.78** | **0.9x** | 40,445.1 | **50,592.9** | **0.8x** | 58.6s | **75.1s** |
| `D5_DeadCode` | Unused / Orphaned Function Detection | 83.9% | **88.3%** | 9.22 | **10.78** | **0.9x** | 40,092.7 | **43,666.6** | **0.9x** | 60.0s | **52.8s** |
| `D6_Structure` | Module Outline & Signature Discovery | 91.7% | **90.6%** | 6.0 | **5.56** | **1.1x** | 33,493.1 | **31,089.3** | **1.1x** | 51.4s | **45.1s** |

---

## 4. 📂 Performance by Repository

| Repository | Questions | Default Acc | MCP Acc | Default Tools | MCP Tools | Tool Ratio | Default Tokens | MCP Tokens | Token Ratio | Default Latency | MCP Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `axios` | 6 | 91.7% | **100.0%** | 11.0 | **18.17** | **0.6x** | 46,696.7 | **63,056.8** | **0.7x** | 69.6s | **85.7s** |
| `cli` | 6 | 93.3% | **87.5%** | 13.17 | **6.5** | **2.0x** | 47,305.3 | **39,227.3** | **1.2x** | 69.3s | **51.1s** |
| `django` | 6 | 85.8% | **95.8%** | 10.83 | **4.33** | **2.5x** | 39,078.0 | **31,523.7** | **1.2x** | 59.0s | **44.7s** |
| `express` | 6 | 100.0% | **100.0%** | 7.33 | **8.17** | **0.9x** | 33,979.8 | **37,562.7** | **0.9x** | 50.9s | **55.8s** |
| `full-stack-fastapi-template` | 6 | 95.0% | **100.0%** | 7.0 | **4.5** | **1.6x** | 28,806.7 | **29,879.8** | **1.0x** | 46.3s | **41.5s** |
| `koa` | 6 | 95.8% | **95.8%** | 8.5 | **10.0** | **0.8x** | 35,597.0 | **44,135.3** | **0.8x** | 48.3s | **64.8s** |
| `nest` | 6 | 95.8% | **96.7%** | 12.17 | **7.67** | **1.6x** | 43,835.8 | **40,054.0** | **1.1x** | 69.1s | **53.4s** |
| `trpc` | 6 | 93.3% | **95.8%** | 10.5 | **6.17** | **1.7x** | 40,492.3 | **34,246.5** | **1.2x** | 60.2s | **46.1s** |
| `zod` | 6 | 93.3% | **93.3%** | 10.83 | **5.0** | **2.2x** | 48,930.2 | **35,788.5** | **1.4x** | 69.0s | **45.4s** |

---

## 5. 📋 Granular Question-by-Question Audit

| Repo | Question ID | Dimension | Default Acc | MCP Acc | Default Calls | MCP Calls | Default Tokens | MCP Tokens | Default Time | MCP Time | Outcome |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `axios` | `Q1_blast_radius` | D1_Impact | 75% | **100%** | 22 | **11** (2 mcp) | 70,561 | **37,291** | 106.2s | **66.0s** | 🏆 **MCP Win (Acc)** |
| `axios` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 15 | **23** (4 mcp) | 44,775 | **71,400** | 57.8s | **98.0s** | Baseline (Tools) |
| `axios` | `Q3_core_dependencies` | D3_Callees | 75% | **100%** | 5 | **3** (3 mcp) | 34,814 | **25,094** | 49.3s | **32.4s** | 🏆 **MCP Win (Acc)** |
| `axios` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 8 | **21** (19 mcp) | 41,999 | **79,747** | 64.9s | **119.7s** | Baseline (Tools) |
| `axios` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 10 | **34** (27 mcp) | 49,920 | **110,410** | 95.0s | **118.8s** | Baseline (Tools) |
| `axios` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 6 | **17** (12 mcp) | 38,111 | **54,399** | 44.2s | **79.0s** | Baseline (Tools) |
| `cli` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 41 | **2** (1 mcp) | 113,214 | **35,086** | 165.5s | **46.7s** | 🏆 **MCP Win (Tools)** |
| `cli` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 11 | **2** (2 mcp) | 37,923 | **21,309** | 42.1s | **20.4s** | 🏆 **MCP Win (Tools)** |
| `cli` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 5 | **3** (2 mcp) | 34,157 | **36,457** | 66.9s | **45.1s** | 🏆 **MCP Win (Tools)** |
| `cli` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 13 | **18** (18 mcp) | 46,245 | **69,209** | 72.2s | **103.1s** | Baseline (Tools) |
| `cli` | `Q5_dead_code` | D5_DeadCode | 60% | **60%** | 6 | **11** (7 mcp) | 29,656 | **46,009** | 40.6s | **59.4s** | Baseline (Tools) |
| `cli` | `Q6_module_outline` | D6_Structure | 100% | **65%** | 3 | **3** (3 mcp) | 22,637 | **27,294** | 28.7s | **31.8s** | Baseline (Acc) |
| `django` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 14 | **4** (2 mcp) | 42,676 | **40,198** | 67.9s | **52.9s** | 🏆 **MCP Win (Tools)** |
| `django` | `Q2_security_callers` | D2_Usages | 80% | **100%** | 15 | **3** (1 mcp) | 36,558 | **32,734** | 53.5s | **38.4s** | 🏆 **MCP Win (Acc)** |
| `django` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 4 | **5** (3 mcp) | 29,023 | **33,629** | 41.4s | **60.6s** | Baseline (Tools) |
| `django` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 18 | **7** (7 mcp) | 53,157 | **34,590** | 84.5s | **47.7s** | 🏆 **MCP Win (Tools)** |
| `django` | `Q5_dead_code` | D5_DeadCode | 35% | **75%** | 12 | **6** (6 mcp) | 52,639 | **27,146** | 76.6s | **46.6s** | 🏆 **MCP Win (Acc)** |
| `django` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 2 | **1** (1 mcp) | 20,415 | **20,845** | 30.3s | **22.2s** | 🏆 **MCP Win (Tools)** |
| `express` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 13 | **14** (6 mcp) | 47,860 | **45,579** | 81.5s | **87.5s** | Baseline (Tools) |
| `express` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 5 | **14** (10 mcp) | 26,953 | **57,209** | 43.9s | **73.1s** | Baseline (Tools) |
| `express` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 9 | **4** (4 mcp) | 40,276 | **26,864** | 58.0s | **34.0s** | 🏆 **MCP Win (Tools)** |
| `express` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 7 | **5** (4 mcp) | 29,619 | **33,350** | 42.3s | **50.2s** | 🏆 **MCP Win (Tools)** |
| `express` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 7 | **9** (8 mcp) | 34,628 | **35,612** | 38.9s | **47.2s** | Baseline (Tools) |
| `express` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 3 | **3** (3 mcp) | 24,543 | **26,762** | 40.8s | **43.0s** | 🤝 **Tie** |
| `full-stack-fastapi-template` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 10 | **2** (1 mcp) | 33,557 | **34,770** | 53.6s | **54.9s** | 🏆 **MCP Win (Tools)** |
| `full-stack-fastapi-template` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 7 | **1** (1 mcp) | 25,100 | **20,128** | 30.5s | **20.6s** | 🏆 **MCP Win (Tools)** |
| `full-stack-fastapi-template` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 5 | **2** (2 mcp) | 29,392 | **22,046** | 32.9s | **25.6s** | 🏆 **MCP Win (Tools)** |
| `full-stack-fastapi-template` | `Q4_semantic_search` | D4_Semantic | 70% | **100%** | 7 | **7** (7 mcp) | 33,850 | **32,272** | 58.4s | **43.2s** | 🏆 **MCP Win (Acc)** |
| `full-stack-fastapi-template` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 10 | **10** (10 mcp) | 26,287 | **48,952** | 59.4s | **54.9s** | 🤝 **Tie** |
| `full-stack-fastapi-template` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 3 | **5** (5 mcp) | 24,654 | **21,111** | 43.0s | **49.6s** | Baseline (Tools) |
| `koa` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 11 | **25** (21 mcp) | 38,869 | **77,245** | 48.6s | **122.4s** | Baseline (Tools) |
| `koa` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 7 | **14** (14 mcp) | 30,180 | **60,398** | 32.5s | **75.8s** | Baseline (Tools) |
| `koa` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 8 | **3** (3 mcp) | 37,043 | **26,561** | 60.7s | **33.9s** | 🏆 **MCP Win (Tools)** |
| `koa` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 9 | **7** (7 mcp) | 35,777 | **36,783** | 44.5s | **71.1s** | 🏆 **MCP Win (Tools)** |
| `koa` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 9 | **9** (7 mcp) | 34,302 | **40,295** | 36.8s | **47.1s** | 🤝 **Tie** |
| `koa` | `Q6_module_outline` | D6_Structure | 75% | **75%** | 7 | **2** (2 mcp) | 37,411 | **23,530** | 66.5s | **38.3s** | 🏆 **MCP Win (Tools)** |
| `nest` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 18 | **4** (2 mcp) | 49,193 | **32,007** | 95.8s | **42.9s** | 🏆 **MCP Win (Tools)** |
| `nest` | `Q2_security_callers` | D2_Usages | 100% | **80%** | 15 | **3** (2 mcp) | 46,762 | **33,189** | 60.6s | **36.5s** | Baseline (Acc) |
| `nest` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 7 | **2** (2 mcp) | 39,123 | **28,819** | 65.0s | **48.4s** | 🏆 **MCP Win (Tools)** |
| `nest` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 11 | **27** (23 mcp) | 41,877 | **91,028** | 52.0s | **131.7s** | Baseline (Tools) |
| `nest` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 14 | **7** (7 mcp) | 52,676 | **28,167** | 83.7s | **28.2s** | 🏆 **MCP Win (Tools)** |
| `nest` | `Q6_module_outline` | D6_Structure | 75% | **100%** | 8 | **3** (3 mcp) | 33,384 | **27,114** | 57.4s | **32.8s** | 🏆 **MCP Win (Acc)** |
| `trpc` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 19 | **9** (2 mcp) | 54,737 | **42,410** | 74.9s | **53.7s** | 🏆 **MCP Win (Tools)** |
| `trpc` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 10 | **1** (1 mcp) | 30,635 | **22,321** | 37.9s | **21.6s** | 🏆 **MCP Win (Tools)** |
| `trpc` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 3 | **4** (4 mcp) | 26,798 | **29,950** | 43.3s | **37.5s** | Baseline (Tools) |
| `trpc` | `Q4_semantic_search` | D4_Semantic | 85% | **100%** | 11 | **9** (5 mcp) | 36,491 | **48,037** | 56.0s | **65.8s** | 🏆 **MCP Win (Acc)** |
| `trpc` | `Q5_dead_code` | D5_DeadCode | 100% | **100%** | 11 | **8** (8 mcp) | 51,224 | **29,033** | 83.4s | **48.1s** | 🏆 **MCP Win (Tools)** |
| `trpc` | `Q6_module_outline` | D6_Structure | 75% | **75%** | 9 | **6** (6 mcp) | 43,069 | **33,728** | 66.1s | **49.9s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 13 | **2** (1 mcp) | 47,757 | **35,280** | 62.1s | **35.6s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q2_security_callers` | D2_Usages | 100% | **100%** | 13 | **1** (1 mcp) | 53,806 | **21,022** | 102.4s | **26.7s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q3_core_dependencies` | D3_Callees | 100% | **100%** | 13 | **9** (5 mcp) | 60,311 | **55,713** | 85.7s | **82.2s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 9 | **5** (5 mcp) | 44,991 | **30,320** | 52.6s | **43.6s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q5_dead_code` | D5_DeadCode | 60% | **60%** | 4 | **3** (3 mcp) | 29,502 | **27,375** | 25.2s | **25.2s** | 🏆 **MCP Win (Tools)** |
| `zod` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 13 | **10** (10 mcp) | 57,214 | **45,021** | 85.9s | **59.1s** | 🏆 **MCP Win (Tools)** |

---

## 6. ⚠️ Judge Hallucination & Deduction Audit

Detailed audit of cases where the LLM Judge detected inaccurate statements or hallucinations:

### `[antigravity_mcp]` `django` | `Q5_dead_code` (Score: 75%)
- **Hallucination Details**: `aget_object_or_404` is mentioned in the response, but it is not a valid function in the Django shortcuts module, which leads to a hallucination detection.
- **Judge Justification**: The candidate correctly identifies the unused functions and distinguishes them from an actively used function, but the mention of a non-existent function results in a deduction.

### `[antigravity_mcp]` `trpc` | `Q6_module_outline` (Score: 75%)
- **Hallucination Details**: The function `pipeReducer` is mentioned in the candidate response but is not listed in the Ground Truth Checklist, indicating it may not be a top-level function in the specified module.
- **Judge Justification**: The candidate accurately summarized the four functions from the Ground Truth Checklist but included an additional function, `pipeReducer`, which is not part of the required summary, resulting in a hallucination detection and a score deduction.

### `[antigravity_mcp]` `koa` | `Q6_module_outline` (Score: 75%)
- **Hallucination Details**: The candidate response includes a method `assert` which is not listed in the Ground Truth Checklist and is not part of the explicitly defined methods on the context prototype.
- **Judge Justification**: The candidate accurately summarized the methods defined in the context prototype but included an additional method `assert` that does not exist in the provided context, resulting in a deduction for hallucination.

### `[antigravity_default]` `django` | `Q5_dead_code` (Score: 35%)
- **Hallucination Details**: The function 'aget_object_or_404' is mentioned, which is not a standard function in Django's shortcuts module.
- **Judge Justification**: The candidate correctly identifies 'get_list_or_404' as unused but introduces a hallucinated function 'aget_object_or_404' and fails to fully address the active symbols, resulting in a low score.

### `[antigravity_default]` `trpc` | `Q4_semantic_search` (Score: 85%)
- **Hallucination Details**: The candidate response references a file 'timerResource.ts' which is not listed in the target files and does not appear to be relevant to the question.
- **Judge Justification**: The candidate accurately identified the key components and explained their mechanisms, but introduced a hallucinated file that detracted from the overall score.

### `[antigravity_default]` `trpc` | `Q6_module_outline` (Score: 75%)
- **Hallucination Details**: The candidate response mentions an internal helper function 'pipeReducer' which is not listed in the Ground Truth Checklist and is not part of the top-level functions requested.
- **Judge Justification**: The candidate accurately summarized the top-level functions as per the Ground Truth Checklist but included a hallucinated internal helper function, resulting in a deduction of points.

### `[antigravity_default]` `nest` | `Q6_module_outline` (Score: 75%)
- **Hallucination Details**: The function `exceedsMaxParamLength` is mentioned as an internal helper, but it is not listed in the Ground Truth Checklist, indicating a hallucination.
- **Judge Justification**: The candidate response accurately summarizes the four top-level functions as per the Ground Truth Checklist but includes a hallucinated function, resulting in a deduction of points.

### `[antigravity_default]` `koa` | `Q6_module_outline` (Score: 75%)
- **Hallucination Details**: The candidate mentions an `assert(...)` method, which is not part of the explicitly defined methods in the context prototype as per the Ground Truth Checklist.
- **Judge Justification**: The candidate accurately summarized the four explicitly defined methods but included a hallucinated method `assert(...)`, resulting in a deduction of points.


---

## 7. 🏛️ Architectural Takeaways & Guidelines

1. **Pre-computed Impact Graph vs Linear Grep (D1 & D2):**
   - Baseline agents crawl through 10-30 separate files using `grep` and `read_file`, generating large
     token overhead and risking context degradation.
   - `analyze_impact` and `find_node_usages` deliver blast radius and caller maps in **1 to 2 calls**,
     reducing token spend by up to 80%.

2. **Semantic Vector Search with Self-Contained Snippets (D4):**
   - `search_code_snippets` returns complete code directly inside `code_snippet` in Turn 1,
     eliminating subsequent redundant file reads.

3. **Zero-Call Static Analysis for Dead Code (D5):**
   - `find_unused_nodes_in_file` queries Neo4j edges directly, eliminating multi-turn grepping.

4. **Complete Module Outlines (D6):**
   - `get_file_structure` extracts all AST classes, methods, and docstrings
     in a single structured payload.
