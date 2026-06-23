# QAD-MultiGuard

> **推测解码 (Speculative Decoding) × 量化感知蒸馏 (QAD-4bit) × 端侧 LLM × 多模态融合 × 差分隐私**
>
> 面向电信反欺诈的软硬协同多模态检测系统

---

## 论文摘要

QAD-MultiGuard 提出了一套端-云协同的电信欺诈检测框架，核心贡献包括：

- **推测解码加速**：草稿模型端侧生成 γ=5 个候选 token（<5ms），云端主模型并行验证，理论加速比 (1−α^(γ+1))/(1−α) ≈ 3.5–4.25×
- **量化感知蒸馏 (QAD)**：FP16 教师模型 → INT4 学生模型（4× 压缩），OV-Freeze 冻结敏感注意力投影层，F1 恢复率 >99%
- **多模态 L-BFGS 融合**：SMS 语义 + 语音声学 + URL 结构 + 元数据，四模态加权融合
- **声学嵌入隐私保护**：128 维非可逆嵌入 Fᵥ，差分隐私高斯机制（ε-LDP），白盒+黑盒 GLO 攻击下 WER ≥ 0.95

---

## 目录结构

```
├── README.md
├── docs/
│   ├── paper1_en_v8.tex                # LaTeX 论文源文件
│   ├── paper v9.docx                    # 论文手稿
│   ├── ref_v4.bib                       # 参考文献
│   ├── FIGURE_CAPTIONS.md              # 图表标题
│   ├── figure/                          # 论文图表输出 (PNG 400dpi + PDF)
│   │   ├── fig2_acoustic_embedding.*    # 128维声学嵌入构造
│   │   ├── fig3_main_results.*          # TAF-28k 主要结果
│   │   ├── fig4_loss_convergence.*      # KL损失收敛 + SNR稳定性
│   │   ├── fig5_loss_teacher_ablation.* # 损失函数 + 教师选择消融
│   │   ├── fig6_ovf_ablation.*          # OV-Freeze 层选择 + 步长比消融
│   │   ├── fig7_speculative_decoding.*  # 推测解码加速比
│   │   └── fig8_revision_ablations.*    # 修订轮次消融实验
│   ├── figure_scripts/                  # 图表生成脚本
│   │   ├── paper_style.py               # 共享期刊样式 (SCI/IEEE-Elsevier)
│   │   ├── paper_data.py                # 数据源
│   │   ├── generate_all.py              # 一键生成全部图表
│   │   └── fig[1-8]_*.py                # 各图表脚本
│   ├── scripts/                         # 论文复现脚本
│   │   ├── download_datasets.py         # 下载 TAF-28k / AdvFraud-3k
│   │   ├── run_paper_simulation.py      # 运行论文仿真实验
│   │   ├── run_full_reproduction.py     # 完整复现流程
│   │   └── verify_paper_alignment.py    # 图表-论文一致性校验
│   ├── datasets/                        # 论文数据集元数据
│   │   ├── TAF28k_metadata.json
│   │   ├── AdvFraud3k_construction_guide.json
│   │   └── ChiFraud/
│   └── superpowers/                     # 设计文档
└── elsarticle/                          # Elsevier LaTeX 模板
```

---

## 图表生成

```bash
cd docs/figure_scripts
pip install matplotlib numpy
python generate_all.py          # 一键生成全部 7 张图 (PNG 400dpi + PDF)
# 或单张生成：
python fig3_main_results.py
```

所有数值由 `paper_data.py` 统一管理，与论文正文和表格保持一致。

---

## 论文复现

```bash
cd docs/scripts
python download_datasets.py     # 下载数据集
python run_paper_simulation.py  # 运行仿真实验
python verify_paper_alignment.py # 校验图表-论文一致性
```

---

## 引用

```bibtex
@article{QAD-MultiGuard,
  title     = {QAD-MultiGuard: ...},
  journal   = {...},
  year      = {2026}
}
```
