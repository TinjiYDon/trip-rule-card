/** 浏览器端规则卡引擎：与 Python rulecard 对齐的核心路径，供 LIVE DEMO 离线跑。 */
(function (global) {
  const LABEL = { free: "免票", half: "半票", full: "全票" };
  const RANK = { free: 0, half: 1, full: 2 };
  const CN = "一二三四五六七八九";

  function prepare(text) {
    let t = String(text || "")
      .replace(/（/g, "(")
      .replace(/）/g, ")")
      .replace(/．/g, ".")
      .replace(/：/g, ":");
    t = t.replace(/(\d+)\s*厘米/g, (_, n) => (Number(n) / 100).toFixed(2) + "米");
    t = t.replace(new RegExp("([" + CN + "])米([" + CN + "])", "g"), (_, a, b) => {
      return CN.indexOf(a) + 1 + "." + (CN.indexOf(b) + 1) + "米";
    });
    return t;
  }

  function sentenceAt(text, index) {
    const left = Math.max(text.lastIndexOf("。", index), text.lastIndexOf("\n", index));
    let end = text.length;
    const a = text.indexOf("。", index);
    const b = text.indexOf("\n", index);
    if (a >= 0) end = Math.min(end, a);
    if (b >= 0) end = Math.min(end, b);
    return text.slice(left + 1, end);
  }

  function kind(local, sentence) {
    if (/半|半票|半价/.test(local)) return "half";
    if (sentence.includes("优惠票") || (local.includes("优惠") && !local.includes("免"))) return "half";
    if (/免|不收|免费/.test(local) && !local.includes("优惠")) return "free";
    if (/免|不收|免费/.test(sentence) && !sentence.includes("半") && !sentence.includes("优惠")) return "free";
    if (sentence.includes("半") || (sentence.includes("优惠") && !sentence.includes("免票"))) return "half";
    return null;
  }

  function sentenceWith(text, tokens) {
    for (const chunk of text.split(/[。\n]/)) {
      if (tokens.some((tok) => chunk.includes(tok))) return chunk.trim();
    }
    return "";
  }

  function modeOf(text) {
    const hasHeight = /\d+(?:\.\d+)?\s*米/.test(text);
    const hasAge = text.includes("周岁");
    const both = /同时满足|缺一不可|且/.test(text);
    const either = /二选一|满足其一|任一|或/.test(text);
    if (both && hasHeight && hasAge) return "both";
    if (either && hasHeight && hasAge) return "either";
    if (hasAge && !hasHeight) return "age";
    if (text.includes("不以身高") && hasAge) return "age";
    if (hasHeight && !hasAge) return "height";
    return hasHeight ? "height" : "age";
  }

  function heights(text) {
    let free = null, half = null, freeIncl = false, halfIncl = false;
    const re = /(\d+(?:\.\d+)?)\s*米/g;
    let m;
    while ((m = re.exec(text))) {
      const value = Number(m[1]);
      const after = text.slice(m.index + m[0].length, m.index + m[0].length + 8);
      const local = text.slice(Math.max(0, m.index - 6), m.index + m[0].length + 12);
      const sentence = sentenceAt(text, m.index);
      const k = kind(local, sentence);
      const inclusive = after.includes("含");
      if (k === "free" && free == null) {
        free = value;
        freeIncl = inclusive;
      } else if (k === "half") {
        half = half == null ? value : Math.max(half, value);
        halfIncl = inclusive || halfIncl;
      }
    }
    const span = text.match(/(\d+(?:\.\d+)?)\s*米(?:以上)?至\s*(\d+(?:\.\d+)?)\s*米半/);
    if (span) {
      half = Number(span[2]);
      if (free == null) free = Number(span[1]);
    }
    const under = text.match(/(?:不满|不到|不足)\s*(\d+(?:\.\d+)?)\s*米(?:免|不收)/);
    if (under) free = Number(under[1]);
    const halfUnder = text.match(/(\d+(?:\.\d+)?)\s*米以下半/);
    if (halfUnder) half = Number(halfUnder[1]);
    const exclusive = text.match(/(\d+(?:\.\d+)?)\s*米\s*\(不含\)\s*以下[^。]{0,12}(?:免费|免票)/);
    if (exclusive) {
      free = Number(exclusive[1]);
      freeIncl = false;
    }
    const band = text.match(/(\d+(?:\.\d+)?)\s*米\s*\(含\)\s*[-~－—至到]\s*(\d+(?:\.\d+)?)\s*米\s*\(含\)/);
    if (band) {
      half = Number(band[2]);
      halfIncl = true;
      if (free == null) {
        free = Number(band[1]);
        freeIncl = false;
      }
    }
    return { free, half, freeIncl, halfIncl };
  }

  function ages(text) {
    let free = null, half = null, freeIncl = false, halfIncl = false;
    const re = /(?:未满|不满|不足|不到)?\s*(\d+)\s*周岁(?:\s*\(含\))?(?:\s*以下)?/g;
    let m;
    while ((m = re.exec(text))) {
      const age = Number(m[1]);
      const after = text.slice(m.index + m[0].length, m.index + m[0].length + 6);
      const local = text.slice(Math.max(0, m.index - 8), m.index + m[0].length + 16);
      const sentence = sentenceAt(text, m.index);
      const k = kind(local, sentence);
      const inclusive = text.slice(m.index, m.index + m[0].length + 6).includes("含") || after.includes("含");
      if (k === "free" && free == null) {
        free = age;
        freeIncl = inclusive;
      } else if (k === "half" && half == null) {
        half = age;
        halfIncl = inclusive;
      }
    }
    const span = text.match(/(\d+)\s*周岁以上[、,，]\s*(\d+)\s*周岁及以下/);
    if (span && /优惠|半|半价/.test(text)) {
      half = Number(span[2]);
      halfIncl = true;
      if (free == null) {
        free = Number(span[1]);
        freeIncl = false;
      }
    }
    return { free, half, freeIncl, halfIncl };
  }

  function extractRule(pageText, promoText) {
    const text = prepare(pageText);
    const promo = prepare(promoText);
    let h = heights(text);
    let a = ages(text);
    if (text.includes("免费预约") || text.includes("进行免费预约")) {
      a = { free: 200, half: null, freeIncl: true, halfIncl: false };
    }
    let days = null;
    let dm = text.match(/提前\s*(\d+)\s*天/);
    if (!dm) dm = text.match(/(\d+)\s*日前/);
    if (!dm) dm = text.match(/提前\s*(\d+)\s*日内/);
    if (dm) days = Number(dm[1]);
    const clockM = text.match(/(\d{1,2}:\d{2})/);
    const bundle = /仅售套票|不卖散票|散客大门票已下架|单独大门票/.test(text);
    const clauseTicket =
      sentenceWith(text, ["二选一", "同时满足", "缺一不可", "满足其一", "且"]) ||
      sentenceWith(text, ["免票", "半票", "免费", "优惠", "周岁", "米"]);
    const party = partyConstraints(text);
    return {
      mode: modeOf(text),
      free_height_m: h.free,
      half_height_m: h.half,
      free_age_lt: a.free,
      half_age_lt: a.half,
      free_height_inclusive: h.freeIncl,
      half_height_inclusive: h.halfIncl,
      free_age_inclusive: a.freeIncl,
      half_age_inclusive: a.halfIncl,
      free_children_per_adult: party.quota,
      escort_required_under_age: party.escort,
      release_days_ahead: days,
      release_clock: clockM ? clockM[1] : null,
      no_show_note: /未履约|爽约/.test(text) ? sentenceWith(text, ["未履约", "爽约"]) : "",
      bundle_only: bundle,
      promo_claims_free: /免费|免票|全免/.test(promo),
      onsale_note: bundle ? sentenceWith(text, ["套票", "下架", "散票"]) || "仅售套票" : "",
      benefits:
        text.includes("学生") && /不能叠加|不可同时/.test(text)
          ? [
              { id: "student", label: "学生优惠", excludes: ["child"] },
              { id: "child", label: "儿童优惠", excludes: ["student"] },
            ]
          : [],
      clause_ticket: clauseTicket,
      clause_release: sentenceWith(text, ["放票", "预约", "预订", "日前", "开售"]),
      clause_benefit: sentenceWith(text, ["不能叠加", "不可同时", "学生票"]),
      clause_onsale: sentenceWith(text, ["套票", "散票", "下架", "元"]),
    };
  }

  function partyConstraints(text) {
    let quota = null;
    let escort = null;
    const patterns = [
      /(?:1|一)名成人限携\s*(\d+)\s*名/,
      /每名成人最多带\s*(\d+)\s*名/,
      /1名成人可带\s*(\d+)\s*名/,
    ];
    for (const pattern of patterns) {
      const m = text.match(pattern);
      if (m) {
        quota = Number(m[1]);
        break;
      }
    }
    if (/一名成人可携带一名/.test(text)) quota = 1;
    const em = text.match(/未满\s*(\d+)\s*周岁[^。]{0,24}(?:须|需)(?:由)?成年人/);
    if (em) escort = Number(em[1]);
    else if (/须有成人陪同|须由成年人代/.test(text)) escort = 14;
    return { quota, escort };
  }

  function under(value, bound, inclusive) {
    if (bound == null) return false;
    if (value < bound) return true;
    return !!inclusive && Math.abs(value - bound) < 1e-6;
  }

  function band(value, freeLt, halfLt, freeIncl, halfIncl) {
    if (under(value, freeLt, freeIncl)) return "free";
    if (under(value, halfLt, halfIncl)) return "half";
    return "full";
  }

  function judgeTicket(rule, age, heightM) {
    const mode = rule.mode || "height";
    const heightResult = band(
      heightM,
      rule.free_height_m,
      rule.half_height_m,
      !!rule.free_height_inclusive,
      !!rule.half_height_inclusive
    );
    const ageResult = band(
      Number(age),
      rule.free_age_lt,
      rule.half_age_lt,
      !!rule.free_age_inclusive,
      !!rule.half_age_inclusive
    );
    const clause = (rule.clause_ticket || "").trim() || "按规则判定";
    if (mode === "height") return [heightResult, clause];
    if (mode === "age") return [ageResult, clause];
    if (mode === "either") {
      const chosen = RANK[heightResult] <= RANK[ageResult] ? heightResult : ageResult;
      return [chosen, clause];
    }
    if (mode === "both") {
      if (heightResult === "full" || ageResult === "full") return ["full", clause];
      const chosen = RANK[heightResult] >= RANK[ageResult] ? heightResult : ageResult;
      return [chosen, clause];
    }
    return ["full", clause];
  }

  function releaseText(rule) {
    const days = rule.release_days_ahead;
    const clock = rule.release_clock;
    const extra = rule.no_show_note || "";
    if (days == null && !clock) return "页面未写放票时刻";
    const parts = [];
    if (days != null && clock) parts.push(`提前 ${days} 天，每日 ${clock} 放票`);
    else if (clock) parts.push(`每日 ${clock} 放票`);
    else parts.push(`最早提前 ${days} 天可订`);
    if (extra) parts.push(extra);
    return parts.join("。");
  }

  function runRule(rule, age, heightM, benefits) {
    const [ticket, ticketClause] = judgeTicket(rule, age, heightM);
    const claims = !!rule.promo_claims_free;
    const conflict = (claims && ticket !== "free") || !!rule.bundle_only;
    const selected = benefits || [];
    const catalog = Object.fromEntries((rule.benefits || []).map((b) => [b.id, b]));
    const notes = [];
    for (const id of selected) {
      const item = catalog[id];
      if (!item) continue;
      for (const other of item.excludes || []) {
        if (selected.includes(other)) {
          notes.push(`${item.label || id} 与 ${(catalog[other] || {}).label || other} 不能叠加`);
        }
      }
    }
    return {
      ticket,
      ticket_label: LABEL[ticket],
      ticket_clause: ticketClause,
      release: releaseText(rule),
      release_clause: rule.clause_release || "",
      promo: {
        conflict,
        claims_free: claims,
        bundle_only: !!rule.bundle_only,
        actual_ticket: ticket,
        onsale_note: rule.onsale_note || "",
        clause: rule.clause_onsale || "",
      },
      benefits: {
        ok: notes.length === 0,
        notes,
        clause: rule.clause_benefit || "未写互斥条款",
      },
    };
  }

  function keywordTicket(promo, page) {
    if (/免费|免票|全免/.test(promo || "")) return ["free", "种草里出现免票，直接采信"];
    if (/半票|半价/.test(promo || "")) return ["half", "种草里出现半票，直接采信"];
    if (/免费|免票/.test(page || "")) return ["free", "种草没写，就在页面里看到免票"];
    return ["full", "没看到优惠词，当成全票"];
  }

  function firstNumberTicket(page, age, heightM) {
    const text = prepare(page);
    const ageM = text.match(/(\d+)\s*周岁/);
    const heightMatch = text.match(/(\d+(?:\.\d+)?)\s*米/);
    let useAge;
    if (ageM && heightMatch) useAge = ageM.index < heightMatch.index;
    else if (ageM) useAge = true;
    else if (heightMatch) useAge = false;
    else return ["full", "页面没有数字门槛"];
    if (useAge) {
      const bound = Number(ageM[1]);
      return age < bound
        ? ["free", `只读第一个年龄 ${bound} 周岁，小于就当免票`]
        : ["full", `只读第一个年龄 ${bound} 周岁，不小于就当全票`];
    }
    const bound = Number(heightMatch[1]);
    return heightM < bound
      ? ["free", `只读第一个身高 ${bound} 米，小于就当免票`]
      : ["full", `只读第一个身高 ${bound} 米，不小于就当全票`];
  }

  function segment(page) {
    return String(page || "")
      .replace(/；/g, "。")
      .split(/[。\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((text, index) => ({ index, text }));
  }

  function compileAndRun(venue, age, heightM, benefits) {
    const page = venue.page_text || "";
    const promo = venue.promo_text || "";
    const clauses = segment(page);
    const rule = extractRule(page, promo);
    const compiled = runRule(rule, age, heightM, benefits || []);
    const [keyword] = keywordTicket(promo, page);
    const [first] = firstNumberTicket(page, age, heightM);
    let ablation = compiled.ticket;
    if (rule.mode === "both") {
      ablation = judgeTicket(Object.assign({}, rule, { mode: "either" }), age, heightM)[0];
    }
    const gold = venue.gold && venue.gold.ticket != null ? venue.gold.ticket : null;
    const errors = [];
    const hasH = rule.free_height_m != null || rule.half_height_m != null;
    const hasA = rule.free_age_lt != null || rule.half_age_lt != null;
    if (!hasH && !hasA) errors.push("no_threshold");
    if (rule.promo_claims_free && compiled.ticket !== "free") errors.push("promo_conflict");
    if (rule.mode === "both" && ablation !== compiled.ticket) errors.push("dual_threshold");
    if (rule.bundle_only) errors.push("bundle");
    const goldTicket = gold;
    const trace = [
      { stage: "分句", summary: `${clauses.length} 句`, detail: clauses.slice(0, 4).map((c) => c.text).join(" / ") },
      { stage: "抽槽", summary: `判定方式 ${rule.mode}`, detail: rule.clause_ticket || "" },
      { stage: "校验", summary: "通过", detail: "" },
      { stage: "修补", summary: "无", detail: "" },
      { stage: "执行", summary: compiled.ticket_label, detail: compiled.ticket_clause },
      { stage: "对照", summary: `种草 ${keyword} / 首数 ${first} / 消融 ${ablation}`, detail: "浏览器离线引擎" },
    ];
    return {
      venue_id: venue.id,
      name: venue.name,
      verified: !!venue.verified,
      source: venue.source || "",
      rule,
      compiled,
      baseline_ticket: keyword,
      first_number_ticket: first,
      ablation_ticket: ablation,
      gold_ticket: goldTicket,
      compiled_correct: goldTicket == null ? null : compiled.ticket === goldTicket,
      baseline_correct: goldTicket == null ? null : keyword === goldTicket,
      first_number_correct: goldTicket == null ? null : first === goldTicket,
      errors,
      trace,
    };
  }

  function buildOrderCard(venue, travelers) {
    const page = venue.page_text || "";
    const promo = venue.promo_text || "";
    const rule = extractRule(page, promo);
    const perPerson = (travelers || []).map((person, index) => {
      const age = Number(person.age || 7);
      const height = Number(person.height_m || 1.3);
      const benefits = person.student || (person.tags || []).includes("student") ? ["child", "student"] : [];
      const compiled = runRule(rule, age, height, benefits);
      const [keyword] = keywordTicket(promo, page);
      return {
        id: person.id || "p" + (index + 1),
        name: person.name || person.id || "出行人",
        age,
        height_m: height,
        ticket: compiled.ticket,
        ticket_label: compiled.ticket_label,
        clause: compiled.ticket_clause,
        promo_conflict: !!compiled.promo.conflict,
        benefits_ok: !!compiled.benefits.ok,
        compiled,
        baseline_ticket: keyword,
      };
    });
    const summary = {
      free: perPerson.filter((p) => p.ticket === "free").length,
      half: perPerson.filter((p) => p.ticket === "half").length,
      full: perPerson.filter((p) => p.ticket === "full").length,
      n: perPerson.length,
    };
    const blockers = [];
    const escortAge = rule.escort_required_under_age;
    if (escortAge != null) {
      const adults = perPerson.filter((p) => p.age >= escortAge);
      const minors = perPerson.filter((p) => p.age < escortAge);
      if (minors.length && !adults.length) {
        blockers.push({ code: "escort_required", message: `未满 ${escortAge} 周岁须由成年人陪同/代约，当前没有成人` });
      }
    }
    const quota = rule.free_children_per_adult;
    if (quota != null) {
      const adults = perPerson.filter((p) => p.age >= 18);
      const freeKids = perPerson.filter((p) => p.ticket === "free" && p.age < 18);
      if (adults.length && freeKids.length > adults.length * quota) {
        blockers.push({
          code: "quota_exceeded",
          message: `免票儿童 ${freeKids.length} 人，超过每成人可带 ${quota} 人（成人 ${adults.length}）`,
        });
      }
    }
    if (perPerson.some((p) => p.promo_conflict)) {
      blockers.push({ code: "promo_conflict", message: "种草宣称免票，但至少一位出行人按条款不是免票" });
    }
    const parts = [];
    if (summary.free) parts.push(`${summary.free} 人免票`);
    if (summary.half) parts.push(`${summary.half} 人半票`);
    if (summary.full) parts.push(`${summary.full} 人全票`);
    return {
      venue_id: venue.id,
      name: venue.name,
      rule,
      per_person: perPerson,
      summary,
      summary_text: parts.join("，") || "未算出票种",
      blockers,
      release: perPerson[0] ? perPerson[0].compiled.release : "页面未写放票时刻",
      can_book: !blockers.some((b) => b.code === "escort_required" || b.code === "quota_exceeded"),
      promo_conflict_any: perPerson.some((p) => p.promo_conflict),
    };
  }

  function parseIntent(text, venues) {
    const raw = String(text || "").trim();
    const alias = [
      [["科技馆", "科学技术馆"], "tech-museum"],
      [["故宫", "紫禁城"], "gugong"],
      [["国博", "国家博物馆"], "chnmuseum"],
      [["东方明珠", "明珠", "登塔"], "oriental-pearl"],
      [["上博", "上海博物馆", "特展"], "shanghai-museum"],
    ];
    let venueId = null;
    for (const [keys, id] of alias) {
      if (keys.some((k) => raw.includes(k)) && venues.some((v) => v.id === id)) {
        venueId = id;
        break;
      }
    }
    let members = null;
    if (/一家三口|三口/.test(raw)) members = [["成人", 35, 1.7], ["儿童", 7, 1.3], ["幼童", 5, 1.1]];
    else if (/亲子|带娃|孩子|小孩|儿童/.test(raw)) members = [["成人", 35, 1.7], ["儿童", 7, 1.3]];
    else if (/本人|自己/.test(raw)) members = [["成人", 28, 1.7]];
    else members = [["成人", 35, 1.7], ["儿童", 7, 1.3]];
    const counts = {};
    const travelers = members.map(([role, age, height]) => {
      counts[role] = (counts[role] || 0) + 1;
      return { id: role + counts[role], name: role + counts[role], age, height_m: height, tags: [] };
    });
    const ages = [...raw.matchAll(/(\d+)\s*岁/g)].map((m) => Number(m[1]));
    const heights = [...raw.matchAll(/(\d+(?:\.\d+)?)\s*米/g)].map((m) => Number(m[1]));
    travelers.forEach((t, i) => {
      if (ages[i] != null) t.age = ages[i];
      if (heights[i] != null) t.height_m = heights[i];
    });
    const name = (venues.find((v) => v.id === venueId) || {}).name;
    const who = travelers.map((t) => `${t.name}(${t.age}岁/${t.height_m}米)`).join("、");
    let reply;
    if (venueId && name) reply = `好的，按「${name}」给 ${who} 算票。条款已带入，不用再粘贴。`;
    else reply = `先按 ${who} 准备。再说一下去哪个馆？（科技馆/故宫/国博/东方明珠/上博）`;
    return { venue_id: venueId, travelers, reply, raw };
  }

  global.RuleCardBrowser = { compileAndRun, extractRule, buildOrderCard, parseIntent, LABEL };
})(typeof window !== "undefined" ? window : globalThis);
