# Demo 视频录制脚本 · EconRefereeOS

> 目标时长：75-90 秒 | 语言：中文 | 上传：Loom (Anyone with link)

## 录制前检查

```bash
cd ~/projects/my-build-with-ag2/econ-refereeos
source ~/projects/build-with-ag2/project-template/.venv/bin/activate
python src/orchestrator.py   # 预跑确认 API 正常（约 30 秒）
```

## 逐秒脚本

### 0:00–0:08 | 开场

**画面**: 终端 + 项目 README

**口播**:
> "EconRefereeOS——经济学论文审稿多智能体系统。四个专业 Agent 协作，输入论文，输出审稿报告。"

### 0:08–0:35 | 运行审稿流水线

**画面**: `python src/orchestrator.py` 运行，展示 4 个 Agent 依次执行

**口播**:
> "第一篇：内置经济学论文——最低工资对就业的影响。Intake Agent 提取五个核心主张。Methods Agent 评估因果识别风险——DID 方法的平行趋势假设、内生性问题。Literature Agent 检查文献覆盖——发现未引用 Neumark & Wascher 2008 等经典文献。Synthesis Agent 整合——建议大修。"

**关键画面**: 终端输出中 4 个 Agent 的进度提示 `[1/4] [2/4] [3/4] [4/4]`

### 0:35–0:55 | 展示审稿报告

**画面**: 滚动展示最终审稿报告的 Markdown 结构

**口播**:
> "最终产出结构化审稿包——总体评价、方法论风险评级、文献缺口、编辑建议。中文输出，直送经济学学术编辑。"

**关键画面**: 报告中 "决定: 大修" 部分 + 推荐审稿人专长

### 0:55–1:10 | 架构说明

**画面**: README 架构图部分

**口播**:
> "四个 Agent 接力流水线。拿来 RefereeOS——AG2 Hackathon 科学赛道第一名——去掉 Daytona 沙箱和 Gemini 依赖，用 DeepSeek 全部替代，零外部服务。十六个 AG2 Beta 技能作为架构参考。"

### 1:10–1:20 | 结束

**画面**: GitHub repo 页面

**口播**:
> "安书伟，C5-AG2，scientific 赛道。仓库公开，README 有 Quick Start。谢谢。"

## 备用：预跑 + 回放方案（75 秒）

如果担心 LLM 响应慢：

```bash
# 预跑保存输出
python src/orchestrator.py 2>&1 | tee /tmp/review_output.txt

# 录制时快速展示（2 秒刷完全部输出）
cat /tmp/review_output.txt
```

简化口播（60 秒）:
- 0:00-0:05 开场
- 0:05-0:20 预跑输出滚动（加速播放）
- 0:20-0:40 展示审稿报告
- 0:40-0:50 架构说明
- 0:50-0:55 结束

## Loom 上传清单

- [ ] 标题: `C5-AG2: EconRefereeOS — 经济学论文审稿多智能体系统`
- [ ] 权限: **"Anyone with the link can view"**
- [ ] 描述中粘贴: `https://github.com/Anshuwei/build-with-ag2/tree/main/econ-refereeos`
