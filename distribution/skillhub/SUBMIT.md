# SkillHub 投稿说明

投稿到 [skillhub.cn](https://skillhub.cn)（中文 AI Skills 社区，Beatra App 也能从这里装 skill）。

本目录是**已经打好的投稿包**，剩下的操作需要你的账号在浏览器里完成。

## 包里有什么

| 文件 | 用途 |
|---|---|
| `zuowen-manju.zip` | Skill 本体，**根目录含 SKILL.md**（硬性要求），25 个文件 88 KB |
| `icon.png` | 图标 512×512（平台要求 64×64 ~ 4096×4096） |
| `overview.png` | 概览图 1280×720（平台要求宽 ≤ 1280） |
| `payload.json` | 表单要填的字段：slug / displayName / summaryZh / overviewMd / version / files |
| `PASTE.md` | **表单粘贴稿** —— 三段文本直接复制，不用从 JSON 里抠 |

## 本次提交：免费版

不配支付通道、不填定价、不开按次结算。先跑通审核、拿反馈，再决定要不要上架
SkillPay 的按次付费版。

免费版的两个卖点写进了简介和详情：

1. **只出 prompt 零依赖零花费** —— 不用装任何东西、不用授权、不用积分
2. **要成片也有路** —— 附带脚本走你自己的 Beatra 积分，账在你那边

## 投递步骤

### 1. 账号

- 绑 GitHub：`/api/v1/auth/github/authorize`
- **绑手机号**（必需，否则提交返回 403 `PHONE_BINDING_REQUIRED`）

### 2. 预检 slug

```
GET /api/v1/community/skills/check-slug?slug=zuowen-manju
```

slug 全局唯一，先确认没被占。

### 3. 上传素材

- 图标 → `POST /api/v1/community/skill-icons/upload`
- 概览图 → `POST /api/v1/community/skills/overview-images/upload`

### 4. 填表提交

打开 <https://skillhub.cn/dashboard/publish>，照着 `PASTE.md` 填（三段文本直接复制）：

- `slug` → `zuowen-manju`
- `displayName` → `作文漫剧`
- `summaryZh` → payload.json 里的 `summaryZh`（中文一句话，审核会看，别写太模糊）
- `overviewMd` → payload.json 里的 `overviewMd`（**已经包含测试案例**，见下）
- `version` → `1.1.0`
- `files` → 上传 `zuowen-manju.zip`

### 5. 审核

提交后进 `/admin/skill-reviews`。平台自己提示的常见不通过原因：

| 原因 | 我们怎么规避的 |
|---|---|
| SKILL.md 格式不规范 | frontmatter 齐全，`name` 与目录名一致 |
| **缺少测试案例** | `SKILL.md` 有「示例」节，`overviewMd` 也有完整的测试案例 |
| 定价明显不合理 | 见下方「定价」 |
| 描述过于模糊 | `summaryZh` 写清了输入、输出、独特之处 |

## 定价（SkillPay）—— 下一阶段再开

本次免费版不开这个。跑通审核、拿到真实使用反馈之后再上。

SkillHub 支持把服务上架成 **Pay Skill，按次调用、实时结算**。
本 skill 每次调用都会消耗 Beatra 积分（图片 90–240/张、视频 225/秒、配音 200/千字），
所以按次计价的收入和积分成本是同向的，**不存在垫资**。

定价前先想清楚三件事：

1. **一次「调用」是什么** —— 一篇作文（8 格图 + 16 秒成片）？还是只出 prompt 不花钱？
2. **积分成本随汇率和模型调价变动** —— 定价要留毛利空间，别按今天的成本卡死
3. **出图不出视频，和出图出视频，价差很大** —— 可以做两档

跑通了再开 Pay Skill。

## GitHub 侧（认领 / 一键导入）

投稿本身不强制 GitHub —— payload 里没有 repo 字段，传 ZIP 即可，账号也能用微信/手机号登录。

但下面三条需要 GitHub：

| 功能 | 需要什么 |
|---|---|
| 一键导入自己的 skill | 绑 GitHub，仓库须在自己账号名下（报错 `github_repo_not_owned`） |
| 被系统扫成「可安装的开源 Plugin」 | 同上 |
| 拿「已认证作者」徽章 | 认领（`/api/v1/skills/claim/batch`） |

仓库地址：`https://github.com/IIEx00/maestro-marketplace.git`

**导入时的路径**：本仓库根目录没有 SKILL.md，skill 在 `skills/zuowen-manju/`。
SkillHub 的导入表单支持指定路径（报错原文是「指定路径不存在 SKILL.md」），
**路径填 `skills/zuowen-manju`** 即可。

若真报 `github_skill_not_found`，说明它只认仓库根的 SKILL.md，
再决定要不要为 GitHub 单开一个只含本 skill 的仓库。

## 重新打包

改了 `skills/zuowen-manju/` 之后要重新生成 zip：

```bash
python3 distribution/skillhub/build.py
```

（`build.py` 负责打 zip、生成图标和概览图、刷新 payload.json。）
