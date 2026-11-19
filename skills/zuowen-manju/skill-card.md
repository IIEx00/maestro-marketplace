## Description:

把中小学生手写的应试作文照片，转成一套可直接出图出片的 AI 漫剧分镜：8 格（可扩 16 格），
中英文生图 prompt、人物定妆图 prompt、错别字与拼音注音登记、以及从分镜到成片的自动化脚本。

默认 L0「原汁原味」——不改错别字、不改病句、不改标点，孩子写错的地方直接当画面梗。
默认 8090 年上海美术电影制片厂画风（水墨/剪纸/敦煌/赛璐璐/木偶/作业本/绘本共 7 种，全部实测）。

## Publisher:

[erosxxx](https://gitee.com/erosxxx)

### License/Terms of Use:

MIT

## Use Case:

**老师、家长、作文培训机构**：把学生的优秀作文做成动画，既是作业也是招生素材。
**内容创作者**：把「小学生的作文 AI 做成动画」做成系列内容，钩子天然自带。

三篇以上做成账号时，共用同一套人物定妆图与作业本外壳（`references/series.md`）。

## Known Risks and Mitigations:

**Risk: 会花钱。** 出图与出视频都按 Beatra credits 计费（视频 225 credits/秒 @480p，
配音 200 credits/1000 字）。批量跑之前必须先 `--dry-run` 看估价。
**Mitigation:** 所有脚本默认只出计划不扣费，必须显式加 `--confirm` 才提交。
`batch_images.py` 付费前会读 live model card 做准入检查（模型可用性、画幅档位、
排除项支持、参考图数量上限），不合规当场拦下，不靠付费试错。

**Risk: 会读用户上传的作文图片。** 图片只做本地转录与出图，不外传原文；
但分镜图会上传到 Beatra 做生成。
**Mitigation:** 转录稿里的姓名、学校、班级、地址一律不写进 prompt（校验脚本硬拦）。

**Risk: 卷面上的老师批改痕迹可能泄进宣发素材。** 分数、扣分、排名、评语属于孩子的负面评价。
**Mitigation:** `references/safety.md` 专列一节「卷面批改痕迹」——进转录稿供家长看，
但不得出现在任何对外素材里，拍的时候避开或后期盖掉。

**Risk: AI 生成内容可能与原文设定不符。** 例如模型自己给不该有人的镜头加人。
**Mitigation:** 每格必须写 `source_text` 指回原文；生成后逐格检图清单
（`references/production-lessons.md` 第七节），发现异常就重出并把问题写进排除项。

**Risk: 参考图会泄漏场景与道具。** 用带场景的分镜图当参考，新镜头会长出参考图里的家具。
**Mitigation:** 人物参考一律用纯背景定妆图；跨场景时显式排除；相邻两格不共用同一张参考图。

## Skill Output:

**Output Type(s):** [Text, Markdown, JSON, Shell commands]

**Output Format:**

```
outputs/<作品名>/
├── storyboard.json      # 机读：每格 prompt、人物、梗
├── storyboard.md        # 人读分镜表
├── source.md            # 转录稿 + 错别字/拼音登记 + 待确认清单
├── production.json      # 出图配方（模式/模型/参考图/排除项）
└── images/              # 图片 + 定妆图 + batch_ledger.json
```

**Output Parameters:** [1D]（格数，默认 8，可扩 16；画幅默认 4:3；档位默认 L0）

**Other Properties Related to Output:**

- 运行时依赖：`beatra-ai-video-studio` skill（提供 `scripts/mcp_client.py`）、Beatra 授权、Pillow、ffmpeg
- 出图/出视频/配音需 Beatra 账号余额；只出 prompt 不花钱
- 批量脚本要求 Beatra 并发 ≤4（平台硬上限），已内建退避重试
