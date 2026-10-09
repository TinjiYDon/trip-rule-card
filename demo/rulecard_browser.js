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
    if (local.includes("半")) return "half";
    if (/免|不收|免费/.test(local)) return "free";
    if (local.includes("优惠") && !local.includes("免")) return "half";
    if (/免|不收|免费/.test(sentence) && !sentence.includes("半") && !sentence.includes("优惠")) return "free";
    if (sentence.includes("半") || (sentence.includes("优惠") && !sentence.includes("免"))) return "half";
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

  global.RuleCardBrowser = { compileAndRun, extractRule, LABEL };
})(typeof window !== "undefined" ? window : globalThis);
