ILANG
TYPE: policy PROJECT: TrueDealAtlas LANG: zh

::STATE{@PROJECT, purpose:真实的美区消费品牌优惠与折扣静态聚合站}
::BOUNDARY{never:编造优惠 编造价格 编造佣金 伪造来源 刷量 绕过登录或反爬|scope=permanent}
::RULE{公开源优先:官方优惠页 sitemap feed; 遵守 robots.txt; 抓不到就不展示}
::RULE{scraper.py 与 build.py 必须读取 .ilang/site.ilang，不得另写厂商清单}
::RULE{运行时纯 Python，无 API 密钥，无付费推理，无服务器}
::ALLOW{action:修改模板 字段解析 样式; condition:保持来源可追溯并通过本地 build 检查}
::ALLOW{action:添加厂商; condition:在 site.ilang 中提供官网和官方优惠入口}
::CHECK{command:python scraper.py && python build.py}
::STATE{@HANDOFF, next_agent:先读本文件与 .ilang/site.ilang，再读 README}
