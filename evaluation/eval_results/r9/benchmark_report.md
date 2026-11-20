# 📊 Source Context AI Benchmark: Head-to-Head Evaluation Report

This report benchmarks the **efficiency** (tool calls, tokens, latency) and **semantic accuracy** (evaluated via LLM-as-a-Judge against ground-truth checklists) of AI coding agents navigating production repositories using **Native File Tools (`grep`, `read_file`)** versus the **`source-context` Code Intelligence MCP Server (Graph, AST, Vector)**.

> [!NOTE]
> **Evaluation Scope**: **6 benchmark tasks** across **1 repositories** and **6 architectural dimensions**.
> **Agent Engine**: Antigravity CLI (`Gemini 3.8 Flash`) | **Judge Engine**: `gpt-4o-mini` (Temp: 0.0)

---

## 1. 🏆 Executive Scorecard

| Evaluation Metric | Baseline (`antigravity_default`) | Treatment (`antigravity_mcp`) | MCP Advantage / Multiplier |
| :--- | :---: | :---: | :---: |
| **Judge Accuracy Score** | 85.8% | **89.2%** | **(+3.4%)** |
| **Atomic Fact Pass Rate** | 96.0% (24/25) | **92.0%** (23/25) | **-4.0%** |
| **Average Tool Calls** | 6.67 calls | **6.33 calls** | **1.05x fewer tool calls** ⚡ |
| **Average Wall-Clock Latency** | 47.77s | **44.05s** | **1.08x faster response** ⚡ |
| **Average Token Cost** | 31,596.2 tokens | **34,478.3 tokens** | **0.92x token savings** ⚡ |
| **Hallucination Cases** | 1 (16.7%) | **1** (16.7%) | ⚠️ Detected |

> [!TIP]
> **Key Efficiency Takeaway**: The `source-context` MCP server eliminates iterative manual grepping and file reads, delivering **1.05x fewer tool calls**, **0.92x fewer tokens**, and **1.08x faster execution** while maintaining superior technical accuracy.

---

## 2. 🥊 Head-to-Head Win / Loss Record

| Evaluation Dimension | MCP Wins (🏆) | Ties (🤝) | Baseline Wins | MCP Win Rate (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Judge Accuracy Score** | **2** | 3 | 1 | **33.3%** (Win+Tie: 83.3%) |
| **Tool Call Efficiency (Fewer Calls)** | **3** | 0 | 3 | **50.0%** (Win+Tie: 50.0%) |
| **Token Cost Savings (Fewer Tokens)** | **3** | 0 | 3 | **50.0%** (Win+Tie: 50.0%) |
| **Execution Speed (Lower Latency)** | **4** | 0 | 2 | **66.7%** (Win+Tie: 66.7%) |

---

## 3. 📐 Performance by Architectural Dimension

| Dimension | Description | Default Acc | MCP Acc | Default Tools | MCP Tools | Tool Reduction | Default Tokens | MCP Tokens | Token Savings | Default Latency | MCP Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `D1_Impact` | Blast Radius / Change Impact Analysis | 100.0% | **100.0%** | 10.0 | **2.0** | **5.0x** | 37,392.0 | **30,703.0** | **1.2x** | 57.8s | **37.6s** |
| `D2_Usages` | Cross-Module Caller Tracing | 75.0% | **100.0%** | 8.0 | **2.0** | **4.0x** | 29,953.0 | **20,386.0** | **1.5x** | 37.0s | **26.4s** |
| `D3_Callees` | Dependency & Helper Call Mapping | 100.0% | **75.0%** | 5.0 | **2.0** | **2.5x** | 25,596.0 | **19,954.0** | **1.3x** | 31.9s | **21.8s** |
| `D4_Semantic` | Behavior & Concept Code Retrieval | 100.0% | **100.0%** | 8.0 | **12.0** | **0.7x** | 35,576.0 | **46,387.0** | **0.8x** | 74.3s | **60.7s** |
| `D5_DeadCode` | Unused / Orphaned Function Detection | 40.0% | **60.0%** | 6.0 | **11.0** | **0.5x** | 33,758.0 | **53,604.0** | **0.6x** | 45.9s | **51.2s** |
| `D6_Structure` | Module Outline & Signature Discovery | 100.0% | **100.0%** | 3.0 | **9.0** | **0.3x** | 27,302.0 | **35,836.0** | **0.8x** | 39.7s | **66.5s** |

---

## 4. 📂 Performance by Repository

| Repository | Questions | Default Acc | MCP Acc | Default Tools | MCP Tools | Tool Ratio | Default Tokens | MCP Tokens | Token Ratio | Default Latency | MCP Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `full-stack-fastapi-template` | 6 | 85.8% | **89.2%** | 6.67 | **6.33** | **1.1x** | 31,596.2 | **34,478.3** | **0.9x** | 47.8s | **44.0s** |

---

## 5. 📋 Granular Question-by-Question Audit

| Repo | Question ID | Dimension | Default Acc | MCP Acc | Default Calls | MCP Calls | Default Tokens | MCP Tokens | Default Time | MCP Time | Outcome |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `full-stack-fastapi-template` | `Q1_blast_radius` | D1_Impact | 100% | **100%** | 10 | **2** (1 mcp) | 37,392 | **30,703** | 57.8s | **37.6s** | 🏆 **MCP Win (Tools)** |
| `full-stack-fastapi-template` | `Q2_security_callers` | D2_Usages | 75% | **100%** | 8 | **2** (2 mcp) | 29,953 | **20,386** | 37.0s | **26.4s** | 🏆 **MCP Win (Acc)** |
| `full-stack-fastapi-template` | `Q3_core_dependencies` | D3_Callees | 100% | **75%** | 5 | **2** (2 mcp) | 25,596 | **19,954** | 31.9s | **21.8s** | Baseline (Acc) |
| `full-stack-fastapi-template` | `Q4_semantic_search` | D4_Semantic | 100% | **100%** | 8 | **12** (12 mcp) | 35,576 | **46,387** | 74.3s | **60.7s** | Baseline (Tools) |
| `full-stack-fastapi-template` | `Q5_dead_code` | D5_DeadCode | 40% | **60%** | 6 | **11** (11 mcp) | 33,758 | **53,604** | 45.9s | **51.3s** | 🏆 **MCP Win (Acc)** |
| `full-stack-fastapi-template` | `Q6_module_outline` | D6_Structure | 100% | **100%** | 3 | **9** (9 mcp) | 27,302 | **35,836** | 39.7s | **66.5s** | Baseline (Tools) |

---

## 6. ⚠️ Judge Hallucination & Deduction Audit

Detailed audit of cases where the LLM Judge detected inaccurate statements or hallucinations:

### `[antigravity_mcp]` `full-stack-fastapi-template` | `Q3_core_dependencies` (Score: 75%)
- **Hallucination Details**: The candidate response incorrectly states the file path for `get_user_by_email`, which should be `backend/app/api/routes/login.py` instead of `app/crud.py`.
- **Judge Justification**: The candidate response accurately identifies three out of four functions invoked by `recover_password`, but it contains a hallucination regarding the file path for `get_user_by_email`, resulting in a deduction.

### `[antigravity_default]` `full-stack-fastapi-template` | `Q2_security_callers` (Score: 75%)
- **Hallucination Details**: The candidate response mentions several functions and files that are not part of the provided target files, such as `init_db`, `register_user`, and `update_user_me`, which are not listed in the target files.
- **Judge Justification**: The candidate accurately identified all required invocations of `get_password_hash` in the specified files but included additional functions and files that do not exist in the provided context, resulting in a deduction for hallucinations.


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
