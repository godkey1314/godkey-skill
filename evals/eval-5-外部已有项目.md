# eval-5：外部已有项目（优雅降级 external 模式）

## 前置条件

- 一个外部开源项目或历史老项目仓库：根目录有 `README.md`、`src/`、`package.json`（或 `pyproject.toml`），但**没有任何 GodKey 文档目录**。

## 用户指令

> 帮我给这个开源项目的 CLI 增加一个 `--format json` 输出选项

## 期望行为检查表

- [ ] 第一步运行 `godkey_gate.py audit`，自动识别为 **`external` 模式**
- [ ] **没有**强行要求用户初始化 `01~09` 中文文档目录，也没有阻塞卡死
- [ ] 读取 `references/开发流程.md`，完整执行防幻觉工程纪律：
  - Pass 0 读原仓库 `README.md` / `docs/` 与依赖版本约束；
  - Pass 1 读全 CLI 入口、参数解析、输出层与既有范式，输出四类文件清单；
  - Pass 2 在对话中输出清晰的改动方案与分层清单再动手；
  - Pass 3 & 4 精准改动、清废、5 维度自检 + 真实 CLI 命令行验证；
  - Pass 5 同步更新原仓库 `README.md` 中的参数说明，并运行 `godkey_gate.py check-sync` 确认

## 反例警报（出现即不通过）

- ❌ 硬阻塞并要求往外部开源仓库强塞 `doc/01-产品介绍` 到 `09-迭代变更`
- ❌ 因为没有 GodKey 文档体系，就直接放弃读全源码、查框架版本、范式对齐与测试验证
- ❌ 改完 CLI 参数却忘记同步原仓库的 `README.md`
