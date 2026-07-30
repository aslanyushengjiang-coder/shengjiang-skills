window.WORKBENCH_CONFIG = {
  "version": 1,
  "id": "ielts-workbench-demo",
  "name": "雅思工作台",
  "owner": "个人学习系统",
  "persona": "IELTS STUDY WORKBENCH",
  "primary_goal": "把每日学习、阅读、错题和复习放进同一个系统",
  "accent": "#2f6b57",
  "modules": [
    {
      "id": "today",
      "title": "今日",
      "type": "tasks",
      "group": "今天",
      "description": "今天最重要的学习任务和完成进度"
    },
    {
      "id": "vocabulary",
      "title": "单词本",
      "type": "knowledge",
      "group": "核心学习",
      "description": "单词记忆、掌握状态和间隔复习"
    },
    {
      "id": "reading",
      "title": "每日阅读",
      "type": "knowledge",
      "group": "核心学习",
      "description": "阅读材料、中文翻译、重点词汇和理解记录"
    },
    {
      "id": "mistakes",
      "title": "错题本",
      "type": "knowledge",
      "group": "核心学习",
      "description": "错题原因、薄弱知识点和定期复习"
    },
    {
      "id": "practice",
      "title": "习题练习",
      "type": "tasks",
      "group": "核心学习",
      "description": "练习计划、正确率和自动回收错题"
    },
    {
      "id": "listening-speaking",
      "title": "听力口语",
      "type": "knowledge",
      "group": "更多",
      "description": "听力素材、跟读和口语练习记录"
    },
    {
      "id": "grammar",
      "title": "语法笔记",
      "type": "knowledge",
      "group": "更多",
      "description": "语法知识点与简明解释"
    },
    {
      "id": "inbox",
      "title": "收集箱",
      "type": "inbox",
      "group": "更多",
      "description": "承接零散资料并建议归入对应模块"
    }
  ],
  "starter_items": {
    "today": [
      {
        "title": "完成一篇每日阅读",
        "status": "doing",
        "note": "阅读文章、查看重点词汇并写一句摘要"
      },
      {
        "title": "复习 20 个薄弱单词",
        "status": "todo",
        "note": "优先复习“似会不会”的词"
      },
      {
        "title": "复盘 3 道主谓一致错题",
        "status": "done",
        "note": "完成后更新错题本状态"
      }
    ],
    "vocabulary": [
      {
        "title": "resilient",
        "status": "new",
        "note": "adj. 有韧性的；能迅速恢复的"
      },
      {
        "title": "decline",
        "status": "reviewed",
        "note": "n./v. 下降；衰退"
      },
      {
        "title": "habitat",
        "status": "new",
        "note": "n. 栖息地"
      }
    ],
    "reading": [
      {
        "title": "Urban Bee Decline",
        "status": "new",
        "note": "The decline of bee populations in urban areas has become a growing concern for ecologists. 重点：habitat loss、urban gardens、pollinators。"
      },
      {
        "title": "Remote Work Trends",
        "status": "reviewed",
        "note": "分析远程办公趋势并记录三个高频表达。"
      }
    ],
    "mistakes": [
      {
        "title": "He, along with his friends, ___ going to the cinema tonight.",
        "status": "new",
        "note": "你的答案：are；正确答案：is。along with 不改变主语单复数。"
      },
      {
        "title": "The number of students ___ increasing.",
        "status": "new",
        "note": "你的答案：are；正确答案：is。the number of 作主语时谓语用单数。"
      },
      {
        "title": "Neither the teacher nor the students ___ satisfied.",
        "status": "reviewed",
        "note": "就近原则：students 是复数，因此使用 are。"
      }
    ],
    "practice": [
      {
        "title": "主谓一致专项练习",
        "status": "doing",
        "note": "目标 10 题；答错自动进入错题本"
      }
    ],
    "listening-speaking": [
      {
        "title": "Part 2：Describe a useful website",
        "status": "new",
        "note": "完成 2 分钟录音并复盘停顿和重复表达"
      }
    ],
    "grammar": [
      {
        "title": "主谓一致",
        "status": "reviewed",
        "note": "along with、together with 不改变主语；neither...nor 使用就近原则。"
      }
    ],
    "inbox": [
      {
        "title": "一篇关于城市生态的英文文章",
        "status": "new",
        "note": "建议归入：每日阅读"
      }
    ]
  }
};
