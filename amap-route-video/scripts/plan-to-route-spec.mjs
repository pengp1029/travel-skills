import {loadOpenClawEnv} from './load-openclaw-env.mjs';

loadOpenClawEnv(import.meta.url);

const MODE_ALIASES = [
  {pattern: /地铁|subway|metro/i, mode: 'transit', preferredVehicle: 'subway'},
  {pattern: /公交|巴士|bus/i, mode: 'transit', preferredVehicle: 'bus'},
  {pattern: /骑行|自行车|bike|bicycle|cycling/i, mode: 'bicycling'},
  {pattern: /步行|走路|walk|walking/i, mode: 'walking'},
  {pattern: /驾车|开车|driving|drive/i, mode: 'driving'},
];

const CITY_ALIASES = [
  '北京', '上海', '天津', '重庆', '广州', '深圳', '杭州', '南京', '苏州', '成都',
  '武汉', '西安', '长沙', '郑州', '青岛', '厦门', '福州', '宁波', '无锡', '合肥',
  '济南', '大连', '沈阳', '哈尔滨', '长春', '石家庄', '太原', '南昌', '南宁', '昆明',
  '贵阳', '兰州', '银川', '西宁', '乌鲁木齐', '海口', '三亚', '珠海', '佛山', '东莞',
  '香港', '澳门', '台北',
];

const normalizeCity = (city) => String(city || '').trim().replace(/市$/, '');

const detectCity = (text) => {
  const envCity = normalizeCity(process.env.AMAP_CITY);
  if (envCity) return envCity;
  const input = String(text || '');
  const explicit = input.match(/(?:城市|city)[:：]\s*([\u4e00-\u9fa5A-Za-z]+?)(?:市)?(?:\s|,|，|。|；|;|$)/i);
  if (explicit?.[1]) return normalizeCity(explicit[1]);
  return CITY_ALIASES.find((city) => input.includes(city)) || '';
};

const stripCityHint = (text, city = detectCity(text)) => {
  let output = String(text || '')
    .replace(/(?:城市|city)[:：]\s*[\u4e00-\u9fa5A-Za-z]+(?:市)?\s*/i, '')
    .trim();
  if (city) {
    output = output
      .replace(new RegExp(`^${city}市?\\s+`), '')
      .replace(new RegExp(`^${city}市?(?=[\\u4e00-\\u9fa5]+(?:->|→|到|至))`), '');
  }
  return output.trim();
};

const normalizeArrow = (text) => stripCityHint(text)
  .replace(/→|到|至/g, '->')
  .replace(/，/g, ',')
  .replace(/。/g, ',')
  .replace(/；/g, ',')
  .replace(/;/g, ',');

const detectMode = (text) => {
  for (const item of MODE_ALIASES) {
    if (item.pattern.test(text)) {
      return {mode: item.mode, preferredVehicle: item.preferredVehicle};
    }
  }
  return {mode: 'walking'};
};

const cleanPlace = (value) => value
  .replace(/^(从|由)/, '')
  .replace(/(出发|开始)$/g, '')
  .trim();

const cleanDestination = (value) => value
  .replace(/(步行|走路|地铁|公交|巴士|骑行|自行车|驾车|开车|一段|路线|方案|到达|前往).*/g, '')
  .trim();

export function parsePlanByRule(input) {
  const text = normalizeArrow(String(input || '').trim());
  const chunks = text.split(',').map((item) => item.trim()).filter(Boolean);
  const segments = [];
  let previousTo = '';

  for (const chunk of chunks) {
    const parts = chunk.split('->').map((item) => item.trim()).filter(Boolean);
    if (parts.length >= 2) {
      const from = cleanPlace(parts[0]);
      const to = cleanDestination(parts.slice(1).join('->'));
      const mode = detectMode(chunk);
      if (from && to) {
        segments.push({from, to, ...mode});
        previousTo = to;
      }
      continue;
    }

    if (previousTo && chunk) {
      const to = cleanDestination(chunk);
      const mode = detectMode(chunk);
      if (to && to !== previousTo) {
        segments.push({from: previousTo, to, ...mode});
        previousTo = to;
      }
    }
  }

  if (segments.length === 0) {
    throw new Error(`无法从输入中解析路线规划：${input}`);
  }

  const city = detectCity(input);
  if (!city) {
    throw new Error('缺少城市信息：请设置 AMAP_CITY，或在路线中写明城市，例如“杭州 西湖->河坊街步行”');
  }

  return {
    title: `${segments[0].from}到${segments[segments.length - 1].to}`,
    city,
    segments,
  };
}

async function parsePlanByLlm(input) {
  const endpoint = process.env.LLM_ENDPOINT;
  const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY;
  if (!endpoint || !apiKey) return null;

  const prompt = `把用户路线规划解析成JSON，只输出JSON。字段：title, city, segments。segments每项字段：from,to,mode,preferredVehicle。mode只能是walking,bicycling,driving,transit。用户输入：${input}`;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: process.env.LLM_MODEL || 'gpt-4o-mini',
      messages: [{role: 'user', content: prompt}],
      temperature: 0,
    }),
  });

  if (!response.ok) {
    throw new Error(`LLM 解析失败：${response.status} ${await response.text()}`);
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || data.answer || '';
  const jsonText = content.replace(/^```json\s*/i, '').replace(/```$/i, '').trim();
  return JSON.parse(jsonText);
}

export async function parsePlan(input) {
  try {
    const llmResult = await parsePlanByLlm(input);
    if (llmResult?.segments?.length) return llmResult;
  } catch (error) {
    console.warn('LLM 解析不可用，改用规则解析：', error.message);
  }
  return parsePlanByRule(input);
}
