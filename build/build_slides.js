// Презентация для лабораторной по детекции заправок.
const pptxgen = require("pptxgenjs");
const path = require("path");

const IMG = "C:/Users/79101/Downloads/Лаба_заправки/slides_img";
const OUT = "C:/Users/79101/Downloads/Лаба_заправки/Лаба_заправки.pptx";

const DARK = "20303A";      // графит приборной панели
const LIGHT = "F4F5F6";
const AMBER = "E39B23";     // топливо
const MUTED = "6B7C87";
const INK = "1A2229";

const H = "Cambria";
const B = "Calibri";
const W = 13.3, HH = 7.5, M = 0.7;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Лаборатория";
pres.title = "Детекция заправок по датчику уровня топлива";

// ---------------------------------------------------------------- helpers
function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: DARK };
  return s;
}

function lightSlide(title) {
  const s = pres.addSlide();
  s.background = { color: LIGHT };
  if (title) {
    s.addText(title, {
      x: M, y: 0.45, w: W - 2 * M, h: 0.8,
      fontSize: 30, bold: true, fontFace: H, color: INK,
      isTextBox: true, margin: 0,
    });
  }
  return s;
}

// нумерованный кружок + заголовок пункта + текст
function iconRow(s, n, y, header, body, opts = {}) {
  const x = opts.x !== undefined ? opts.x : M;
  const w = opts.w !== undefined ? opts.w : W - 2 * M - 0.9;
  s.addShape(pres.ShapeType.ellipse, {
    x: x, y: y, w: 0.52, h: 0.52, fill: { color: AMBER },
  });
  s.addText(String(n), {
    x: x, y: y, w: 0.52, h: 0.52, align: "center", valign: "middle",
    fontSize: 16, bold: true, color: DARK, fontFace: B, isTextBox: true, margin: 0,
  });
  s.addText(header, {
    x: x + 0.75, y: y - 0.04, w: w, h: 0.34,
    fontSize: 17, bold: true, color: INK, fontFace: B, isTextBox: true, margin: 0,
  });
  s.addText(body, {
    x: x + 0.75, y: y + 0.32, w: w, h: opts.bodyH || 0.75,
    fontSize: 14, color: MUTED, fontFace: B, isTextBox: true, margin: 0,
  });
}

function card(s, x, y, w, h, opts = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || "FFFFFF" },
    line: { color: opts.line || "E1E5E8", width: 1 },
  });
}

function stat(s, x, y, w, value, label, color) {
  s.addText(value, {
    x, y, w, h: 0.85, fontSize: 44, bold: true, fontFace: H,
    color: color || AMBER, align: "center", isTextBox: true, margin: 0,
  });
  s.addText(label, {
    x, y: y + 0.85, w, h: 0.5, fontSize: 12, fontFace: B,
    color: MUTED, align: "center", isTextBox: true, margin: 0,
  });
}

// ================================================================= 1. титул
{
  const s = darkSlide();
  s.addText("Детекция заправок\nпо датчику уровня топлива", {
    x: M, y: 1.9, w: 8.6, h: 2.0,
    fontSize: 40, bold: true, fontFace: H, color: "FFFFFF",
    lineSpacing: 46, isTextBox: true, margin: 0,
  });
  s.addText("Лабораторная работа на реальных данных автопарка", {
    x: M, y: 4.05, w: 8.6, h: 0.5,
    fontSize: 18, fontFace: B, color: AMBER, isTextBox: true, margin: 0,
  });
  s.addText("50 машин  ·  6.1 млн сообщений телематики  ·  полгода работы", {
    x: M, y: 4.65, w: 8.6, h: 0.4,
    fontSize: 14, fontFace: B, color: "9FB0BB", isTextBox: true, margin: 0,
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 10.1, y: 2.3, w: 2.5, h: 2.5, fill: { color: AMBER },
  });
  s.addText("F1\n0.85", {
    x: 10.1, y: 2.3, w: 2.5, h: 2.5, align: "center", valign: "middle",
    fontSize: 30, bold: true, fontFace: H, color: DARK, isTextBox: true, margin: 0,
  });
  s.addText("бейзлайн, который\nнужно побить", {
    x: 10.1, y: 5.0, w: 2.5, h: 0.7, align: "center",
    fontSize: 12, fontFace: B, color: "9FB0BB", isTextBox: true, margin: 0,
  });
  s.addNotes("Лаба про то, как из шумного ряда датчика достать события заправок. " +
    "Данные реальные, метрики честные, в конце задание на улучшение.");
}

// ================================================================= 2. зачем
{
  const s = lightSlide("Зачем это нужно");
  s.addText(
    "Топливо — одна из самых крупных статей расходов автопарка. Контролируют его " +
    "по датчику уровня в баке: если заправки и сливы не находятся автоматически, " +
    "топливный баланс сводят руками по чекам, а расхождения списывают на «погрешность датчика».",
    { x: M, y: 1.4, w: W - 2 * M, h: 1.0, fontSize: 16, fontFace: B, color: INK,
      isTextBox: true, margin: 0 });

  const cw = 3.7, gap = 0.35;
  const xs = [M, M + cw + gap, M + 2 * (cw + gap)];
  const data = [
    ["1 249", "заправок размечено\nза полгода"],
    ["57 %", "из них — с заглушенным\nдвигателем"],
    ["1.8 %", "доля целевого класса\nв данных"],
  ];
  xs.forEach((x, i) => {
    card(s, x, 2.75, cw, 2.0);
    stat(s, x, 3.05, cw, data[i][0], data[i][1]);
  });

  s.addText("Задача: по ряду уровня топлива находить моменты заправок.", {
    x: M, y: 5.15, w: W - 2 * M, h: 0.5,
    fontSize: 18, bold: true, fontFace: B, color: INK, isTextBox: true, margin: 0,
  });
  s.addNotes("57% = 711 из 1249 событий приходятся на заправки при заглушенном двигателе.");
}

// ================================================================= 3. что меряет ДУТ
{
  const s = lightSlide("Что приходит с машины");
  s.addText(
    "Телематический блок шлёт сообщение раз в несколько секунд. Нас интересуют четыре поля.",
    { x: M, y: 1.35, w: W - 2 * M, h: 0.4, fontSize: 15, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0 });

  const rows = [
    ["уровень топлива", "сырые «попугаи» датчика, не литры"],
    ["зажигание", "0 или 1 — включён ли двигатель"],
    ["скорость", "нужна, чтобы отличить стоянку от движения"],
    ["время", "сообщения приходят неравномерно"],
  ];
  rows.forEach((r, i) => {
    const y = 2.0 + i * 1.0;
    card(s, M, y, 5.6, 0.82);
    s.addText(r[0], { x: M + 0.25, y: y + 0.06, w: 2.3, h: 0.32,
      fontSize: 15, bold: true, fontFace: B, color: INK, isTextBox: true, margin: 0 });
    s.addText(r[1], { x: M + 0.25, y: y + 0.42, w: 5.1, h: 0.32,
      fontSize: 12, fontFace: B, color: MUTED, isTextBox: true, margin: 0 });
  });

  card(s, 6.9, 2.0, W - M - 6.9, 3.82, { fill: "FFFFFF" });
  s.addText("Тарировка", { x: 7.2, y: 2.25, w: 5.1, h: 0.4,
    fontSize: 20, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "Датчик отдаёт число, зависящее от геометрии бака. У каждой машины своя " +
    "тарировочная таблица: несколько пар «показание → литры». Между узлами — " +
    "линейная интерполяция.\n\n" +
    "Без этого шага одна и та же заправка на 40 литров даёт на разных машинах " +
    "разную амплитуду, и ни общий порог, ни общая модель не работают.",
    { x: 7.2, y: 2.75, w: 5.1, h: 2.9, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });
}

// ================================================================= 4. почему не производная
{
  const s = lightSlide("Почему не решается производной");
  s.addText("Очевидное решение — порог на приросте уровня. Ломается по трём причинам.", {
    x: M, y: 1.35, w: W - 2 * M, h: 0.4, fontSize: 15, fontFace: B, color: MUTED,
    isTextBox: true, margin: 0 });

  iconRow(s, 1, 2.05, "Датчик молчит при заглушенном двигателе",
    "Он запитан от зажигания. А заправка — это почти всегда стоянка с заглушенным " +
    "двигателем. Роста уровня в данных просто нет: есть провал и другое значение после.");
  iconRow(s, 2, 3.35, "Уровень плещется на ходу",
    "Разгоны, торможения, уклон дороги — уровень гуляет на несколько литров. " +
    "Медленная заправка из бензовоза похожа на этот шум.");
  iconRow(s, 3, 4.65, "Порог не выбирается",
    "Низкий порог ловит подливы, но срабатывает на плеске. Высокий игнорирует плеск, " +
    "но пропускает мелкие заправки. Середины нет.");

  s.addText("Пороговое правило на наших данных: событийный F1 = 0.37", {
    x: M, y: 6.0, w: W - 2 * M, h: 0.45,
    fontSize: 16, bold: true, fontFace: B, color: AMBER, isTextBox: true, margin: 0 });
}

// ================================================================= 5. ключевой факт
{
  const s = darkSlide();
  s.addText("Ключевой факт", {
    x: M, y: 1.5, w: W - 2 * M, h: 0.5,
    fontSize: 18, fontFace: B, color: AMBER, isTextBox: true, margin: 0 });
  s.addText("Датчик запитан от зажигания.\nДвигатель заглушен — данных нет.", {
    x: M, y: 2.2, w: W - 2 * M, h: 1.8,
    fontSize: 36, bold: true, fontFace: H, color: "FFFFFF", lineSpacing: 44,
    isTextBox: true, margin: 0 });
  s.addText(
    "Из этого следует, что одно и то же физическое событие оставляет в данных " +
    "два совершенно разных следа. Значит, это не одна задача детекции, а две.",
    { x: M, y: 4.3, w: 9.5, h: 1.0, fontSize: 17, fontFace: B, color: "9FB0BB",
      isTextBox: true, margin: 0, lineSpacing: 26 });
  s.addNotes("Это главная мысль всей лабы. Дальше вся конструкция вырастает отсюда.");
}

// ================================================================= 6. две задачи
{
  const s = lightSlide("Две задачи вместо одной");
  const cw = 5.95, gap = 0.3;
  const x1 = M, x2 = M + cw + gap;

  card(s, x1, 1.5, cw, 4.3);
  s.addText("Двигатель заглушен", { x: x1 + 0.3, y: 1.75, w: cw - 0.6, h: 0.45,
    fontSize: 21, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "Роста уровня нет вообще. Последнее сообщение до глушения даёт уровень «до», " +
    "первое после запуска — уровень «после». Между ними блок нулей произвольной длины.\n\n" +
    "Что делаем: весь блок нулей схлопываем в одну точку. Событие занимает ровно " +
    "три точки — до, ноль, после.\n\n" +
    "711 событий в данных",
    { x: x1 + 0.3, y: 2.3, w: cw - 0.6, h: 3.3, fontSize: 13.5, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0, lineSpacing: 19 });

  card(s, x2, 1.5, cw, 4.3, { fill: "FFFFFF", line: AMBER });
  s.addText("Двигатель работает", { x: x2 + 0.3, y: 1.75, w: cw - 0.6, h: 0.45,
    fontSize: 21, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "Уровень растёт монотонно 10–20 минут. Это видно напрямую, но тонет в шуме " +
    "посекундных сообщений.\n\n" +
    "Что делаем: ресемплим ряд в 5-минутные бины, уровень бина — среднее по " +
    "валидным сообщениям.\n\n" +
    "538 событий в данных — это наша цель на лабе",
    { x: x2 + 0.3, y: 2.3, w: cw - 0.6, h: 3.3, fontSize: 13.5, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0, lineSpacing: 19 });

  s.addText("Разные представления данных, разные модели, разные метрики.", {
    x: M, y: 6.05, w: W - 2 * M, h: 0.45,
    fontSize: 16, bold: true, fontFace: B, color: INK, isTextBox: true, margin: 0 });
}

// ================================================================= 7. пример события
{
  const s = lightSlide("Как выглядит заправка на ходу");
  s.addImage({ path: path.join(IMG, "s_event.png"), x: M, y: 1.5, w: 8.4, h: 3.495 });
  s.addText(
    "Один бин — 5 минут. Заправка занимает 3–4 бина: уровень растёт с 17 до 75 литров, " +
    "потом выходит на полку.\n\n" +
    "Серым — разметка оператора. Она грубая: границы поставлены на глаз, поэтому " +
    "требовать от модели попадания бин-в-бин бессмысленно.",
    { x: 9.4, y: 1.6, w: W - M - 9.4, h: 3.2, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });
  s.addText("Задача модели: отличить такой рост от плеска и от шума датчика.", {
    x: M, y: 5.35, w: W - 2 * M, h: 0.45,
    fontSize: 16, bold: true, fontFace: B, color: INK, isTextBox: true, margin: 0 });
}

// ================================================================= 8. данные лабы
{
  const s = lightSlide("Датасет лабораторной");
  s.addText("Файл fuel_5min.csv — 85 228 строк, 4.4 МБ. Одна строка — 5 минут жизни одной машины.", {
    x: M, y: 1.35, w: W - 2 * M, h: 0.4, fontSize: 15, fontFace: B, color: MUTED,
    isTextBox: true, margin: 0 });

  const cols = [
    ["vehicle", "машина, V01…V50"],
    ["ts", "начало интервала"],
    ["fuel", "средний уровень, литры"],
    ["ign", "доля времени с зажиганием"],
    ["speed", "средняя скорость"],
    ["n_msg", "сообщений в бине"],
    ["label", "0 / 1 / 2"],
    ["split", "train или test"],
  ];
  cols.forEach((c, i) => {
    const x = i < 4 ? M : M + 3.3;
    const y = 2.0 + (i % 4) * 0.62;
    s.addText(c[0], { x, y, w: 1.15, h: 0.32, fontSize: 13, bold: true,
      fontFace: "Courier New", color: AMBER, isTextBox: true, margin: 0 });
    s.addText(c[1], { x: x + 1.2, y, w: 2.05, h: 0.5, fontSize: 12,
      fontFace: B, color: MUTED, isTextBox: true, margin: 0 });
  });

  card(s, 7.2, 1.9, W - M - 7.2, 3.6, { fill: "FFFFFF", line: AMBER });
  s.addText("Разбиение — по машинам", { x: 7.5, y: 2.15, w: 4.9, h: 0.4,
    fontSize: 19, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "45 машин в train, 5 в test. Тестовые машины модель не видит вообще.\n\n" +
    "Если резать случайно по точкам, окна одного и того же события попадут " +
    "и в обучение, и в тест — метрика будет завышена, а на новой машине модель " +
    "развалится.\n\n" +
    "Это самая частая ошибка в задачах на временных рядах.",
    { x: 7.5, y: 2.65, w: 4.9, h: 2.7, fontSize: 13.5, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 19 });

  s.addText("Классы: 0 — ничего · 1 — заправка на ходу (цель) · 2 — заправка на стоянке", {
    x: M, y: 5.75, w: W - 2 * M, h: 0.4, fontSize: 14, fontFace: B, color: INK,
    isTextBox: true, margin: 0 });
}

// ================================================================= 9. дисбаланс
{
  const s = lightSlide("Дисбаланс классов");
  s.addImage({ path: path.join(IMG, "s_balance.png"), x: M, y: 1.7, w: 7.0, h: 3.673 });
  s.addText(
    "Целевой класс — 1.8% бинов.\n\n" +
    "Модель «всегда 0» даст 98% accuracy и не найдёт ни одной заправки. " +
    "Поэтому accuracy здесь не метрика.\n\n" +
    "Что делаем: веса классов в функции потерь. Но не обратно пропорционально " +
    "частоте — такой вес улетает в десятки, и модель начинает видеть заправки везде. " +
    "Берём корень из отношения частот.",
    { x: 8.1, y: 1.7, w: W - M - 8.1, h: 3.6, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });
  s.addText("вес класса = min( √(N_max / N_класса), 30 )", {
    x: M, y: 5.7, w: W - 2 * M, h: 0.45, fontSize: 17, bold: true,
    fontFace: "Courier New", color: AMBER, isTextBox: true, margin: 0 });
}

// ================================================================= 10. признаки
{
  const s = lightSlide("Признаки и окна");
  const cw = 3.73, gap = 0.35;
  const xs = [M, M + cw + gap, M + 2 * (cw + gap)];

  card(s, xs[0], 1.5, cw, 4.1);
  s.addText("Признаки бина", { x: xs[0] + 0.28, y: 1.75, w: cw - 0.56, h: 0.4,
    fontSize: 18, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "fuel — сам уровень\n\nd1, d2, d3, d4 — разности с уровнем на 1, 2, 3 и 4 бина назад\n\n" +
    "Разная глубина не случайна: d1 ловит резкий скачок, d4 — медленный рост, " +
    "размазанный на 20 минут.",
    { x: xs[0] + 0.28, y: 2.25, w: cw - 0.56, h: 3.1, fontSize: 13.5, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0, lineSpacing: 19 });

  card(s, xs[1], 1.5, cw, 4.1);
  s.addText("Окно", { x: xs[1] + 0.28, y: 1.75, w: cw - 0.56, h: 0.4,
    fontSize: 18, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "7 бинов подряд = 35 минут.\n\nКласс окна — класс его центрального бина.\n\n" +
    "Центр, а не конец: для ответа «была ли тут заправка» одинаково полезен " +
    "контекст и до, и после момента.",
    { x: xs[1] + 0.28, y: 2.25, w: cw - 0.56, h: 3.1, fontSize: 13.5, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0, lineSpacing: 19 });

  card(s, xs[2], 1.5, cw, 4.1, { fill: "FFFFFF", line: AMBER });
  s.addText("Что получилось", { x: xs[2] + 0.28, y: 1.75, w: cw - 0.56, h: 0.4,
    fontSize: 18, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "74 993 окна в обучении\n9 935 окон в тесте\n\n5 признаков × 7 шагов на окно\n\n" +
    "Никаких порогов, подобранных руками, и никакого сглаживающего фильтра — " +
    "всё это модель должна вывести сама.",
    { x: xs[2] + 0.28, y: 2.25, w: cw - 0.56, h: 3.1, fontSize: 13.5, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0, lineSpacing: 19 });
}

// ================================================================= 11. модель
{
  const s = lightSlide("Модель");
  s.addText("Двухслойная LSTM. Ровно та, что работает в проде — обученную на лабе можно забрать в сервис.", {
    x: M, y: 1.35, w: W - 2 * M, h: 0.4, fontSize: 15, fontFace: B, color: MUTED,
    isTextBox: true, margin: 0 });

  const steps = [
    ["вход", "7 × 5"],
    ["LSTM", "2 слоя × 64"],
    ["dropout", "0.2"],
    ["линейный", "64 → 3"],
    ["выход", "3 класса"],
  ];
  const bw = 2.15, bgap = 0.28;
  steps.forEach((st, i) => {
    const x = M + i * (bw + bgap);
    card(s, x, 2.1, bw, 1.3, { fill: i === 1 ? DARK : "FFFFFF" });
    s.addText(st[0], { x, y: 2.35, w: bw, h: 0.35, align: "center",
      fontSize: 15, bold: true, fontFace: B, color: i === 1 ? "FFFFFF" : INK,
      isTextBox: true, margin: 0 });
    s.addText(st[1], { x, y: 2.75, w: bw, h: 0.35, align: "center",
      fontSize: 13, fontFace: "Courier New", color: i === 1 ? AMBER : MUTED,
      isTextBox: true, margin: 0 });
  });

  const facts = [
    ["51 651", "параметр"],
    ["30", "эпох"],
    ["45 с", "обучение на CPU"],
    ["512", "размер батча"],
  ];
  facts.forEach((f, i) => {
    stat(s, M + i * 3.1, 4.0, 2.9, f[0], f[1], i === 2 ? AMBER : INK);
  });

  s.addText(
    "Модель крошечная. Это осознанно: задача про правильную постановку и правильную " +
    "метрику, а не про размер сети. Экспериментировать дёшево — полный цикл обучения " +
    "меньше минуты.",
    { x: M, y: 5.6, w: W - 2 * M, h: 0.8, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });
}

// ================================================================= 12. точечные метрики
{
  const s = lightSlide("Точечные метрики обманывают");
  s.addText(
    "Оператору автопарка не нужен ответ «этот пятиминутный бин относится к заправке». " +
    "Ему нужно «14 августа в 10:05 машина V11 заправилась». Это событие, а не точка.",
    { x: M, y: 1.35, w: W - 2 * M, h: 0.8, fontSize: 16, fontFace: B, color: INK,
      isTextBox: true, margin: 0, lineSpacing: 22 });

  card(s, M, 2.5, 5.95, 2.9);
  s.addText("Угадала 3 бина из 5", { x: M + 0.3, y: 2.75, w: 5.35, h: 0.4,
    fontSize: 18, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "По точечной метрике — посредственный результат.\n\n" +
    "По событийной — идеально: заправка найдена, оператор её увидит.",
    { x: M + 0.3, y: 3.25, w: 5.35, h: 1.9, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });

  card(s, M + 6.25, 2.5, 5.95, 2.9);
  s.addText("Один бин посреди стоянки", { x: M + 6.55, y: 2.75, w: 5.35, h: 0.4,
    fontSize: 18, bold: true, fontFace: H, color: INK, isTextBox: true, margin: 0 });
  s.addText(
    "По точечной метрике — почти незаметно на фоне 9 935 бинов.\n\n" +
    "По событийной — полноценное ложное срабатывание, оператор пошёл разбираться зря.",
    { x: M + 6.55, y: 3.25, w: 5.35, h: 1.9, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });

  s.addText("Мерить нужно то, чем пользуются.", {
    x: M, y: 5.7, w: W - 2 * M, h: 0.45, fontSize: 18, bold: true,
    fontFace: B, color: AMBER, isTextBox: true, margin: 0 });
}

// ================================================================= 13. событийная метрика
{
  const s = lightSlide("Событийная метрика");
  iconRow(s, 1, 1.6, "Собираем события",
    "Предсказанные и эталонные события — это непрерывные блоки класса 1 внутри одной машины.",
    { bodyH: 0.5 });
  iconRow(s, 2, 2.65, "Сопоставляем с допуском ±5 минут",
    "Предсказание считается попаданием, если пересекается с эталонным событием с точностью до пяти минут.",
    { bodyH: 0.5 });
  iconRow(s, 3, 3.7, "Не штрафуем за неоднозначное",
    "Предсказание, попавшее на класс 2, не считаем ошибкой: разметке там доверять нельзя.",
    { bodyH: 0.5 });
  iconRow(s, 4, 4.75, "Считаем TP, FP, FN по событиям",
    "И уже из них — precision, recall и F1. Это главная метрика лабы.",
    { bodyH: 0.5 });

  s.addText("Допуск ±5 минут — это ровно один бин. Соседний бин не считается ошибкой.", {
    x: M, y: 5.95, w: W - 2 * M, h: 0.45, fontSize: 15, fontFace: B, color: MUTED,
    isTextBox: true, margin: 0 });
}

// ================================================================= 14. результат
{
  const s = lightSlide("Результат бейзлайна");
  s.addImage({ path: path.join(IMG, "s_confusion.png"), x: M, y: 1.6, w: 3.77, h: 4.0 });

  const rows = [
    ["точечный F1, класс 1", "0.750"],
    ["событийная precision", "1.000"],
    ["событийная recall", "0.744"],
    ["событийный F1", "0.853"],
    ["найдено / пропущено", "96 / 33"],
  ];
  rows.forEach((r, i) => {
    const y = 1.75 + i * 0.72;
    s.addText(r[0], { x: 6.0, y, w: 3.6, h: 0.4, fontSize: 15, fontFace: B,
      color: MUTED, isTextBox: true, margin: 0 });
    s.addText(r[1], { x: 9.6, y: y - 0.06, w: 1.5, h: 0.45, fontSize: 20, bold: true,
      fontFace: H, color: i >= 3 ? AMBER : INK, align: "right", isTextBox: true, margin: 0 });
  });

  s.addText(
    "Ложных срабатываний по событиям ноль: все лишние бины оказались рядом с настоящими " +
    "заправками и попали в допуск. Весь запас для улучшения — в 33 пропущенных событиях. " +
    "И обратите внимание на матрицу: 72 бина заправки на ходу модель отправила в класс 2.",
    { x: 6.0, y: 5.4, w: W - M - 6.0, h: 1.1, fontSize: 13, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 18 });
}

// ================================================================= 15. сравнение
{
  const s = lightSlide("Зачем здесь модель");
  s.addImage({ path: path.join(IMG, "s_compare.png"), x: M, y: 1.7, w: 6.2, h: 3.758 });
  s.addText(
    "Пороговое правило перебрано по всей сетке порогов от 1 до 20 литров. " +
    "Лучший результат — 0.373.\n\n" +
    "Причина видна в цифрах: при любом пороге recall высокий, а precision около 0.22. " +
    "Правило находит все заправки и вместе с ними ещё вчетверо больше плеска.\n\n" +
    "Модель отличает рост от шума по форме окна, а не по одному числу.",
    { x: 7.4, y: 1.7, w: W - M - 7.4, h: 3.7, fontSize: 14, fontFace: B, color: MUTED,
      isTextBox: true, margin: 0, lineSpacing: 20 });
  s.addText("Разница более чем вдвое — и это на честном разбиении по машинам.", {
    x: M, y: 5.8, w: W - 2 * M, h: 0.45, fontSize: 16, bold: true, fontFace: B,
    color: INK, isTextBox: true, margin: 0 });
}

// ================================================================= 16. задание
{
  const s = darkSlide();
  s.addText("Задание", {
    x: M, y: 0.6, w: W - 2 * M, h: 0.7,
    fontSize: 34, bold: true, fontFace: H, color: "FFFFFF", isTextBox: true, margin: 0 });
  s.addText("Увеличить событийный F1 на тестовых машинах. Планка «хорошо» — выше 0.88.", {
    x: M, y: 1.4, w: W - 2 * M, h: 0.45, fontSize: 17, fontFace: B, color: AMBER,
    isTextBox: true, margin: 0 });

  const ideas = [
    ["Признаки", "ign, speed, n_msg, время суток"],
    ["Нормализация", "статистики только по train"],
    ["Длина окна", "35 минут — не догма"],
    ["Веса классов", "другая степень, focal loss"],
    ["Архитектура", "biLSTM, GRU, 1D-CNN"],
    ["Постобработка", "убрать одиночные срабатывания"],
    ["Порог вероятности", "argmax — тоже не догма"],
    ["Размер бина", "есть сырые данные"],
  ];
  const cw = 2.78, ch = 1.0, gx = 0.26, gy = 0.25;
  ideas.forEach((it, i) => {
    const x = M + (i % 4) * (cw + gx);
    const y = 2.15 + Math.floor(i / 4) * (ch + gy);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: cw, h: ch, rectRadius: 0.08,
      fill: { color: "2C3F4B" }, line: { color: "3D5361", width: 1 },
    });
    s.addText(it[0], { x: x + 0.2, y: y + 0.14, w: cw - 0.4, h: 0.32,
      fontSize: 14, bold: true, fontFace: B, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(it[1], { x: x + 0.2, y: y + 0.48, w: cw - 0.4, h: 0.42,
      fontSize: 11.5, fontFace: B, color: "9FB0BB", isTextBox: true, margin: 0 });
  });

  s.addText(
    "Правила: разбиение split не трогаем · на тестовых машинах не обучаемся · " +
    "гиперпараметры подбираем на train · в отчёте таблица «что поменял → какой стал F1»",
    { x: M, y: 4.95, w: W - 2 * M, h: 0.8, fontSize: 14, fontFace: B, color: "9FB0BB",
      isTextBox: true, margin: 0, lineSpacing: 20 });
  s.addText("Подгонка гиперпараметров по тесту не засчитывается.", {
    x: M, y: 5.85, w: W - 2 * M, h: 0.45, fontSize: 15, bold: true, fontFace: B,
    color: AMBER, isTextBox: true, margin: 0 });
}

// ================================================================= 17. со звёздочкой
{
  const s = darkSlide();
  s.addText("Вопрос со звёздочкой", {
    x: M, y: 1.1, w: W - 2 * M, h: 0.7,
    fontSize: 30, bold: true, fontFace: H, color: "FFFFFF", isTextBox: true, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 2.1, w: 5.6, h: 2.5, rectRadius: 0.08,
    fill: { color: "2C3F4B" }, line: { color: "3D5361", width: 1 },
  });
  s.addText("100 %", { x: M, y: 2.45, w: 5.6, h: 1.0, align: "center",
    fontSize: 54, bold: true, fontFace: H, color: AMBER, isTextBox: true, margin: 0 });
  s.addText("accuracy второй модели —\nдля заправок при заглушенном двигателе",
    { x: M, y: 3.5, w: 5.6, h: 0.9, align: "center", fontSize: 13, fontFace: B,
      color: "9FB0BB", isTextBox: true, margin: 0, lineSpacing: 18 });

  s.addText(
    "Разметка там ставится по правилу: блок ровно из трёх точек, в середине уровень " +
    "равен нулю, слева и справа уровни стабильны и различаются.\n\n" +
    "Признаки модели — уровень и его разности.\n\n" +
    "Почему стопроцентный результат в такой постановке ничего не говорит о качестве " +
    "детекции? Что нужно поменять, чтобы число стало осмысленным?",
    { x: 6.9, y: 2.1, w: W - M - 6.9, h: 3.0, fontSize: 15, fontFace: B, color: "C9D4DB",
      isTextBox: true, margin: 0, lineSpacing: 22 });

  s.addText("Умение увидеть такую ловушку в своих же метриках — половина работы дата-сайентиста.", {
    x: M, y: 5.6, w: W - 2 * M, h: 0.5, fontSize: 15, fontFace: B, color: AMBER,
    isTextBox: true, margin: 0 });
  s.addNotes("Ответ: метка детерминированно выводится из тех же признаков, что подаются " +
    "на вход. Модель восстанавливает правило разметки, а не учит физику заправки. " +
    "Признак утечки — идеальное разделение класса 1:1400 на второй эпохе. " +
    "Нужны метки, независимые от ряда уровня: чеки АЗС, транзакции топливных карт.");
}

pres.writeFile({ fileName: OUT }).then(() => {
  console.log("сохранено:", OUT);
});
