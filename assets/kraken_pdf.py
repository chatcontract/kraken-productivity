#!/usr/bin/env python3
"""
kraken_pdf.py — the single PDF renderer for every Kraken Productivity skill.

Why this file exists
--------------------
Every skill in this plugin used to describe its PDF in prose and let the model
hand-write reportlab code at run time. That produced real, shipped corruption:

  * `stream inflate: invalid distance too far back` — a broken zlib content
    stream, so page 1 silently lost most of its drawing operators.
  * `Unknown operator 'e627529T882353'` — computed coordinates written into the
    content stream in scientific notation, which is not valid PDF syntax.
  * A near-empty first page: the timeline drew as a bare rule with axis labels
    and no dots, the "Today's meetings" heading vanished, and the meeting list
    resumed mid-way down page 2.
  * No footer on page 1, so the brief looked truncated.

The fix is to stop improvising geometry. Skills now emit a JSON payload and call
this module, which is deterministic, hardened against all four failure modes
above, and self-verifying.

Usage
-----
    python3 kraken_pdf.py --kind daily_brief --in brief.json --out Daily_Brief_2026-09-09.pdf
    python3 kraken_pdf.py --kind call_prep   --in call.json  --out 1200-acme.pdf
    python3 kraken_pdf.py --batch manifest.json        # many PDFs, one process

Exit codes
----------
    0  PDF written and passed every check
    2  bad input (missing file, unparseable JSON, unknown kind)
    3  render failed
    4  PDF was produced but FAILED verification (corrupt stream, blank page,
       missing footer, or wrong page count). The file is left on disk for
       inspection, but the caller must treat this as a failure.
    5  the content does not fit the 2-page ceiling — call_prep AND
       daily_brief. The message names what to cut, in priority order, and the
       rejected file is deleted so nothing stale can be attached. Cut content
       and render again; never shrink type and never pad with a blank page.
    6  the payload does not match the documented format for its kind — a
       section was dropped, a field that must carry content is empty, or the
       accuracy gate caught a defect that makes the document wrong: a status
       outside the six-word vocabulary, a Completed claim with no source, an
       actionable item with no action/owner/by_when, an owner of "you" or
       "team", or more than six discovery questions. The message names every
       offending key and item. Fix the payload; do not bypass it.

Accuracy warnings
-----------------
Softer defects — a related_to pointing at no real question, a citation
missing from the Sources list, placeholder text left in — print as
ACCURACY WARNING lines on stderr and do NOT change the exit code. Failing a
whole brief to protect a footnote would lose the document for the sake of
the citation, which is the wrong trade; but a defect that only prints is a
defect that ships, so read them.

The caller never needs to rasterize or eyeball the output. If this script exits
0, the PDF is sound.

Markdown backup
----------------
Every render ALSO writes a plain-text markdown copy of the same payload —
same sections, same order, same content — next to the PDF (default: the
--out path with .md in place of .pdf; override with --md-out, or a "md" key
per job in --batch). This is not optional and does not depend on the PDF
succeeding: a payload that fails FormatError still gets no backup (there is
no verified content yet), but any payload that reaches rendering gets one
regardless of what happens to the mail attachment afterward. This exists
because an attachment can fail to reach the user for reasons this script
cannot see or verify (a sandbox/mail-tool quirk) — the skill's Delivery step
should always name the markdown path in its own summary so nothing is a
total loss.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# HARDENING 1 — must happen before anything from reportlab.platypus is used.
# --------------------------------------------------------------------------
# useA85=0 keeps streams inline-previewable in browsers.
# pageCompression=0 is the direct fix for "invalid distance too far back": with
# no Flate stage there is no zlib block to corrupt, and any future syntax
# problem stays a visible local error instead of destroying a whole page.
try:
    import reportlab.rl_config  # noqa: E402
except ImportError:  # pragma: no cover - dependency preflight
    sys.stderr.write(
        "DEPENDENCY ERROR: reportlab is not installed, so no PDF can be "
        "rendered.\n  Install it with:  pip install --break-system-packages "
        "reportlab pypdf pypdfium2\n"
        "    reportlab   required — renders the PDF\n"
        "    pypdf       required — counts pages and decodes streams for "
        "verification\n"
        "    pypdfium2   optional — adds the near-empty-page check; without "
        "it that\n                one check is skipped and everything else "
        "still runs\n"
        "  Until then, the calling skill must fall back to sending its "
        "content inline in the email body (never a silent failure, and "
        "never hand-written PDF code).\n")
    sys.exit(3)

reportlab.rl_config.useA85 = 0
reportlab.rl_config.pageCompression = 0
reportlab.rl_config.invariant = 0
reportlab.rl_config.warnOnMissingFontGlyphs = 0

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfgen import canvas as pdfcanvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Palette and metrics — single source of truth for all three skills.
# --------------------------------------------------------------------------
# Hex strings kept alongside the Color objects — inline <font color="..."> runs
# need the string form, and re-deriving it from a reportlab Color is unreliable.
INK_HEX = "#0B0D10"
INK_SOFT_HEX = "#565B62"
INK_TERTIARY_HEX = "#8B909A"
RULE_HEX = "#E4E6EA"
ALERT_HEX = "#D2542E"
ALERT_BOLD_HEX = "#B5431F"
SUCCESS_HEX = "#0D720A"
ACCENT_BG_HEX = "#FBF3F0"

# Semantic roles. Colour carries meaning here or it is not used at all: a
# palette that decorates is a palette the reader learns to ignore.
#   INFO    blue    context, "what you need to know"
#   ACTION  green   an action with an owner (SUCCESS reused — same green)
#   RISK    amber   watch this
#   CRITICAL red    urgent, blocked, overdue (ALERT_BOLD reused)
#   SECOND  grey    secondary and metadata (INK_SOFT/INK_TERTIARY reused)
INFO_HEX = "#1B4F9C"
RISK_HEX = "#9A6207"
INFO_BG_HEX = "#F1F5FB"
RISK_BG_HEX = "#FDF6E9"
TABLE_BG_HEX = "#F7F8FA"


INK = colors.HexColor(INK_HEX)
INK_SOFT = colors.HexColor(INK_SOFT_HEX)
INK_TERTIARY = colors.HexColor(INK_TERTIARY_HEX)
RULE = colors.HexColor(RULE_HEX)
ALERT = colors.HexColor(ALERT_HEX)
ALERT_BOLD = colors.HexColor(ALERT_BOLD_HEX)
SUCCESS = colors.HexColor(SUCCESS_HEX)
ACCENT_BG = colors.HexColor(ACCENT_BG_HEX)
INFO = colors.HexColor(INFO_HEX)
RISK = colors.HexColor(RISK_HEX)
INFO_BG = colors.HexColor(INFO_BG_HEX)
RISK_BG = colors.HexColor(RISK_BG_HEX)
TABLE_BG = colors.HexColor(TABLE_BG_HEX)

# One semantic lookup, so no caller invents its own mapping.
SEMANTIC = {
    "info": (INFO, INFO_HEX, INFO_BG),
    "action": (SUCCESS, SUCCESS_HEX, None),
    "risk": (RISK, RISK_HEX, RISK_BG),
    "critical": (ALERT_BOLD, ALERT_BOLD_HEX, ACCENT_BG),
    "secondary": (INK_SOFT, INK_SOFT_HEX, None),
}

PAGE_W, PAGE_H = LETTER
MARGIN = 0.9 * inch          # one page geometry for every document
CALL_PREP_MARGIN = MARGIN    # retained name; both kinds share it now

# --------------------------------------------------------------------------
# The reading grid — used by every document this renderer produces.
# --------------------------------------------------------------------------
# The brief used to set its body across the full 6.5in measure at 10pt, which
# is 100-110 characters per line — far past the 65-75 that reads comfortably,
# and the real reason a complete brief felt like a wall of text rather than
# something you could skim at 8:55am.
#
# So every document sets on a two-column grid: a narrow left gutter carrying
# the label and the source citation, and a ~4.95in reading column (~74
# characters) for the substance. Moving citations into the gutter also pulls
# them out of the body flow, where an italic grey line under every single
# claim was the other half of the density problem.
# The gap lives INSIDE the gutter column as its right padding, so the two
# columns sum to exactly the frame width. (It was briefly subtracted from the
# text column as well, which left 0.18in of dead measure and stopped every
# grid row short of the full-width section rules.)
DOC_GUTTER = 1.75 * inch
DOC_GAP = 0.2 * inch


# --------------------------------------------------------------------------
# HARDENING 2 — every number that reaches the content stream goes through num().
# --------------------------------------------------------------------------
def num(value, places: int = 3) -> float:
    """Clamp a computed coordinate to a plain fixed-point float.

    A tiny value such as 6.27529e-07 formats as "6.27529e-07" in a PDF content
    stream, which the parser reads as the operator `e627529T882353`. Rounding to
    3 decimal places collapses anything that small to 0.0, so scientific
    notation can never be emitted. Also neutralizes NaN/inf, which reportlab
    would otherwise write out verbatim.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v or v in (float("inf"), float("-inf")):  # NaN / inf
        return 0.0
    v = round(v, places)
    # round() can still hand back -0.0; normalize it.
    if v == 0:
        return 0.0
    return v


def esc(text) -> str:
    """Escape gathered content so it is data, never markup or instructions.

    Everything the skills read (email, chat, calendar, transcripts) passes
    through here. Angle brackets would otherwise be parsed as reportlab inline
    markup and could unbalance the paragraph, and control characters can break
    the text-showing operator.
    """
    if text is None:
        return ""
    s = str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Quotes matter because esc() output is also interpolated into XML
    # ATTRIBUTES — a link's href. Left raw, one quote in a connector-supplied
    # URL closes the attribute early and the parser rejects the paragraph,
    # taking the whole render down with exit 3.
    s = s.replace('"', "&quot;").replace("'", "&#39;")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)
    return s.strip()


def bold(text) -> str:
    """Escaped text wrapped in a bold run."""
    return "<b>%s</b>" % esc(text)


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
def build_styles(scale: float = 1.0):
    """Paragraph styles. `scale` only ever moves within a narrow band and is
    used solely by the call-prep exact-2-page fitter."""

    def sz(pt):
        return num(pt * scale, 2)

    return {
        "headline": ParagraphStyle(
            "headline", fontName="Times-Bold", fontSize=sz(19), leading=sz(23),
            textColor=INK, spaceAfter=sz(5), alignment=TA_LEFT,
        ),
        "stat": ParagraphStyle(
            "stat", fontName="Helvetica", fontSize=sz(9.5), leading=sz(13),
            textColor=INK_SOFT, spaceAfter=sz(2),
        ),
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=sz(12.5), leading=sz(16),
            textColor=INK, spaceBefore=sz(16), spaceAfter=sz(6),
        ),
        "section_alert": ParagraphStyle(
            "section_alert", fontName="Helvetica-Bold", fontSize=sz(12.5), leading=sz(16),
            textColor=ALERT, spaceBefore=sz(16), spaceAfter=sz(6),
        ),
        "section_success": ParagraphStyle(
            "section_success", fontName="Helvetica-Bold", fontSize=sz(12.5), leading=sz(16),
            textColor=SUCCESS, spaceBefore=sz(16), spaceAfter=sz(6),
        ),
        "item_title": ParagraphStyle(
            "item_title", fontName="Helvetica-Bold", fontSize=sz(10.5), leading=sz(14),
            textColor=INK, spaceBefore=sz(7), spaceAfter=sz(1),
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=sz(10), leading=sz(13.5),
            textColor=INK_SOFT, spaceAfter=sz(2),
        ),
        "meta": ParagraphStyle(
            "meta", fontName="Helvetica", fontSize=sz(9), leading=sz(12),
            textColor=INK_SOFT, spaceAfter=sz(1),
        ),
        "source": ParagraphStyle(
            "source", fontName="Helvetica-Oblique", fontSize=sz(9), leading=sz(12),
            textColor=INK_TERTIARY, spaceAfter=sz(2),
        ),
        "empty": ParagraphStyle(
            "empty", fontName="Helvetica-Oblique", fontSize=sz(9.5), leading=sz(13),
            textColor=INK_TERTIARY, spaceAfter=sz(2),
        ),
        "fix": ParagraphStyle(
            "fix", fontName="Helvetica", fontSize=sz(10), leading=sz(13.5),
            textColor=INK_SOFT, spaceBefore=sz(2), spaceAfter=sz(2),
        ),
        "doc_title": ParagraphStyle(
            "doc_title", fontName="Times-Bold", fontSize=sz(20), leading=sz(24),
            textColor=INK, spaceAfter=sz(3),
        ),
        "objective": ParagraphStyle(
            "objective", fontName="Helvetica-Bold", fontSize=sz(10.5), leading=sz(14.5),
            textColor=INK,
        ),
        "action": ParagraphStyle(
            "action", fontName="Helvetica-Bold", fontSize=sz(10.5), leading=sz(14),
            textColor=INK, spaceBefore=sz(1), spaceAfter=sz(3),
        ),
        "subhead": ParagraphStyle(
            "subhead", fontName="Helvetica-Bold", fontSize=sz(9.5), leading=sz(13),
            textColor=INK_SOFT, spaceBefore=sz(8), spaceAfter=sz(2),
        ),

        # ---- call prep only: the reading grid ----
        # Body is near-ink rather than grey, and leading is opened from 13.5
        # to 15, because a 45-minute-old grey 10pt wall is the thing this
        # brief is read against the clock.
        "doc_body": ParagraphStyle(
            "doc_body", fontName="Helvetica", fontSize=sz(10), leading=sz(15),
            textColor=INK, spaceAfter=sz(3),
        ),
        # The gutter: label above, citation beneath, both small and quiet.
        "doc_label": ParagraphStyle(
            "doc_label", fontName="Helvetica-Bold", fontSize=sz(8.5), leading=sz(11),
            textColor=INK_SOFT, spaceAfter=sz(1),
        ),
        "doc_cite": ParagraphStyle(
            "doc_cite", fontName="Helvetica", fontSize=sz(8), leading=sz(10.5),
            textColor=INK_TERTIARY, spaceAfter=sz(1),
        ),
        "doc_item_title": ParagraphStyle(
            "doc_item_title", fontName="Helvetica-Bold", fontSize=sz(10.5),
            leading=sz(14), textColor=INK, spaceAfter=sz(2),
        ),
        # Sections get more air above them than the daily brief's 16pt, so a
        # reader scanning for one heading can actually find its edges.
        # --- compact set, for the 2-page briefings ---
        "glance_label": ParagraphStyle(
            "glance_label", fontName="Helvetica-Bold", fontSize=sz(6.6),
            leading=sz(8.4), textColor=INK_TERTIARY, spaceAfter=sz(1)),
        "glance_value": ParagraphStyle(
            "glance_value", fontName="Helvetica", fontSize=sz(8.6),
            leading=sz(11), textColor=INK, spaceAfter=sz(0)),
        "cell": ParagraphStyle(
            "cell", fontName="Helvetica", fontSize=sz(8.4), leading=sz(10.8),
            textColor=INK, spaceAfter=sz(0)),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName="Helvetica-Bold", fontSize=sz(8.4),
            leading=sz(10.8), textColor=INK, spaceAfter=sz(0)),
        "cell_soft": ParagraphStyle(
            "cell_soft", fontName="Helvetica", fontSize=sz(7.6), leading=sz(9.6),
            textColor=INK_SOFT, spaceAfter=sz(0)),
        "cell_head": ParagraphStyle(
            "cell_head", fontName="Helvetica-Bold", fontSize=sz(6.8),
            leading=sz(8.6), textColor=INK_TERTIARY, spaceAfter=sz(0)),
        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica", fontSize=sz(9), leading=sz(12.4),
            textColor=INK, spaceAfter=sz(3), leftIndent=sz(10),
            firstLineIndent=sz(-10)),
        "tight_section": ParagraphStyle(
            "tight_section", fontName="Helvetica-Bold", fontSize=sz(9.4),
            leading=sz(11.6), textColor=INK, spaceBefore=sz(9),
            spaceAfter=sz(3)),
        "doc_section": ParagraphStyle(
            "doc_section", fontName="Helvetica-Bold", fontSize=sz(11),
            leading=sz(14), textColor=INK_SOFT, spaceBefore=sz(19),
            spaceAfter=sz(7),
        ),
    }


# --------------------------------------------------------------------------
# HARDENING 3 — the timeline, as a real Flowable with balanced graphics state.
# --------------------------------------------------------------------------
class Timeline(Flowable):
    """One horizontal rule with a dot per meeting, positioned by start time and
    sized by duration.

    The old version drew this by pushing raw operator strings onto the canvas,
    which is what corrupted page 1 and left a bare axis with no dots. This draws
    only through reportlab primitives, brackets the whole thing in
    saveState/restoreState, and routes every coordinate through num().
    """

    def __init__(self, meetings, width, height=54):
        Flowable.__init__(self)
        self.meetings = meetings or []
        self.width = num(width)
        self.height = num(height)

    def wrap(self, availWidth, availHeight):
        self.width = num(availWidth)
        return self.width, self.height

    @staticmethod
    def _minutes(value):
        """Accept 'HH:MM', 'H:MM am/pm', or a raw minutes-from-midnight number."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return num(value, 0)
        s = str(value).strip().lower().replace(".", "")
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)?$", s)
        if not m:
            m = re.match(r"^(\d{1,2})\s*(am|pm)$", s)
            if not m:
                return None
            hour, minute, mer = int(m.group(1)), 0, m.group(2)
        else:
            hour, minute, mer = int(m.group(1)), int(m.group(2)), m.group(3)
        if mer == "pm" and hour != 12:
            hour += 12
        if mer == "am" and hour == 12:
            hour = 0
        return num(hour * 60 + minute, 0)

    def draw(self):
        canv = self.canv
        canv.saveState()  # balanced restoreState below — non-negotiable
        try:
            starts = []
            for mt in self.meetings:
                s = self._minutes(mt.get("start"))
                if s is not None:
                    starts.append(s)

            # Axis window. Defaults to a normal working day, widened to cover
            # anything outside it (the 11:30pm event in the real brief).
            lo, hi = 7 * 60, 18 * 60
            if starts:
                lo = min(lo, min(starts) - 30)
                hi = max(hi, max(starts) + 60)
            lo = max(0, num(lo, 0))
            hi = min(24 * 60, num(hi, 0))
            span = num(hi - lo, 0) or 1.0

            axis_y = num(self.height * 0.42)
            left, right = 0.0, num(self.width)
            usable = num(right - left)

            def x_at(minutes):
                frac = (num(minutes, 0) - lo) / span
                frac = min(1.0, max(0.0, frac))
                return num(left + frac * usable)

            # The rule.
            canv.setStrokeColor(RULE)
            canv.setLineWidth(num(1.0))
            canv.line(left, axis_y, right, axis_y)

            # Hour ticks and alternating labels.
            canv.setFont("Helvetica", 7)
            canv.setFillColor(INK_TERTIARY)
            first_hour = int((lo + 59) // 60)
            last_hour = int(hi // 60)
            step = 3 if (last_hour - first_hour) > 8 else 2
            idx = 0
            for hour in range(first_hour, last_hour + 1):
                if hour % step:
                    continue
                x = x_at(hour * 60)
                canv.setStrokeColor(RULE)
                canv.setLineWidth(num(0.75))
                canv.line(x, num(axis_y - 3), x, num(axis_y + 3))
                h12 = hour % 12 or 12
                # hour 24 is midnight, not noon — the naive form printed "12pm".
                meridiem = "am" if (hour < 12 or hour >= 24) else "pm"
                label = "%d%s" % (h12, meridiem)
                label_y = num(axis_y + 9) if idx % 2 == 0 else num(axis_y - 14)
                canv.drawCentredString(x, label_y, label)
                idx += 1

            # One dot per meeting. Radius tracks duration so a two-hour block
            # reads heavier than a fifteen-minute stand-up.
            for mt in self.meetings:
                start = self._minutes(mt.get("start"))
                if start is None:
                    continue
                end = self._minutes(mt.get("end"))
                dur = 30.0
                if end is not None and end > start:
                    dur = num(end - start, 0)
                radius = num(min(5.6, max(2.4, 2.4 + (dur / 120.0) * 3.2)), 2)

                x = x_at(start)
                kind = str(mt.get("kind") or "").strip().lower()

                if kind == "conflict":
                    canv.setFillColor(ALERT)
                    canv.setStrokeColor(ALERT)
                    canv.setLineWidth(num(1.1))
                    canv.circle(x, axis_y, radius, stroke=0, fill=1)
                    canv.circle(x, axis_y, num(radius + 2.4), stroke=1, fill=0)
                elif kind in ("back_to_back", "back-to-back"):
                    canv.setFillColor(INK_SOFT)
                    canv.circle(x, axis_y, radius, stroke=0, fill=1)
                    canv.setStrokeColor(ALERT)
                    canv.setLineWidth(num(0.9))
                    canv.setDash(1, 2)
                    canv.circle(x, axis_y, num(radius + 2.4), stroke=1, fill=0)
                    canv.setDash()  # clear the dash before the next shape
                else:
                    canv.setFillColor(INK_SOFT)
                    canv.circle(x, axis_y, radius, stroke=0, fill=1)
        finally:
            canv.restoreState()


class AccentBox(Flowable):
    """Shaded cell with a colored left border — the single accent on call-prep
    page 2. Wraps a pre-wrapped Paragraph so height is known before drawing."""

    def __init__(self, para, width, pad=7):
        Flowable.__init__(self)
        self.para = para
        self.width = num(width)
        self.pad = num(pad)
        self._h = 0.0

    def wrap(self, availWidth, availHeight):
        self.width = num(availWidth)
        _, ph = self.para.wrap(num(self.width - 2 * self.pad - 4), availHeight)
        self._h = num(ph + 2 * self.pad)
        return self.width, self._h

    def draw(self):
        canv = self.canv
        canv.saveState()
        try:
            canv.setFillColor(ACCENT_BG)
            canv.rect(0, 0, self.width, self._h, stroke=0, fill=1)
            canv.setFillColor(ALERT)
            canv.rect(0, 0, num(2.6), self._h, stroke=0, fill=1)
            self.para.drawOn(canv, num(self.pad + 4), self.pad)
        finally:
            canv.restoreState()


class HRule(Flowable):
    def __init__(self, width, color=RULE, thickness=0.75, space=0):
        Flowable.__init__(self)
        self.width = num(width)
        self.color = color
        self.thickness = num(thickness)
        self.height = num(thickness + space)

    def wrap(self, availWidth, availHeight):
        self.width = num(availWidth)
        return self.width, self.height

    def draw(self):
        canv = self.canv
        canv.saveState()
        try:
            canv.setStrokeColor(self.color)
            canv.setLineWidth(self.thickness)
            canv.line(0, 0, self.width, 0)
        finally:
            canv.restoreState()


# --------------------------------------------------------------------------
# HARDENING 4 — two-pass footer that stamps EVERY page, page 1 included.
# --------------------------------------------------------------------------
class NumberedCanvas(pdfcanvas.Canvas):
    """Collects page state on showPage and stamps "Page X of Y" at save() time.

    The previous implementation stamped inside showPage, so the final page never
    got a footer and — depending on flush order — neither did page 1. Here every
    collected state is replayed and stamped, which is why the footer count is
    verifiable afterwards.
    """

    def __init__(self, *args, **kwargs):
        self._footer = kwargs.pop("footer_label", "Page %(page)d of %(total)d")
        self._suppress_single = kwargs.pop("suppress_single_page_footer", False)
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_states = []

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            if not (self._suppress_single and total == 1):
                self._stamp(total)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _stamp(self, total):
        self.saveState()
        try:
            self.setFont("Helvetica", 8)
            self.setFillColor(INK_TERTIARY)
            label = self._footer % {"page": self._pageNumber, "total": total}
            self.drawRightString(num(PAGE_W - MARGIN), num(MARGIN * 0.52), label)
        finally:
            self.restoreState()


def _doc(path, margin=MARGIN, title="Brief"):
    doc = BaseDocTemplate(
        path,
        pagesize=LETTER,
        leftMargin=num(margin),
        rightMargin=num(margin),
        topMargin=num(margin),
        bottomMargin=num(margin),
        title=title,
        author="Kraken Productivity",
        subject=title,
    )
    frame = Frame(
        num(doc.leftMargin), num(doc.bottomMargin),
        num(doc.width), num(doc.height),
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="body",
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])
    return doc


# --------------------------------------------------------------------------
# Shared section helpers
# --------------------------------------------------------------------------
def section(story, styles, heading, tone="plain"):
    """Section header. Never wrapped in a KeepTogether with its whole section —
    that is what ejected the entire meetings block to page 2 and left page 1
    empty. The header is glued to its FIRST item only, by add_item below."""
    style = {
        "alert": styles["section_alert"],
        "success": styles["section_success"],
    }.get(tone, styles["section"])
    story.append(Paragraph(esc(heading), style))


def _status_color(status):
    """Map a status label to a palette hex color.

    Only the leading word decides the colour, so a status may carry a
    descriptive tail — "Waiting on Jane", "New discussion point", "Completed
    9 Sep via Slack". The vocabulary itself is NOT free-form: accuracy_check
    hard-fails any status outside the six documented ones (§4), so the
    fall-through below is a safety net, not a licence."""
    s = (status or "").strip().lower()
    if s.startswith(("complet", "resolv", "done", "closed")):
        return SUCCESS_HEX
    if s.startswith("block"):
        return ALERT_BOLD_HEX
    if s.startswith("wait"):
        return ALERT_HEX
    if s.startswith(("needs confirm", "unconfirmed", "confirm")):
        return INK_TERTIARY_HEX
    if s.startswith("new"):
        return INK_HEX
    return INK_SOFT_HEX  # "open" and anything unrecognized


def add_item(story, styles, title=None, lines=None, source=None,
             fix=None, first=False, header=None, header_tone="plain",
             owner=None, by_when=None, action=None, status=None):
    """One item, kept together as a unit. If `first`, the section header rides
    along so a heading can never be orphaned at the foot of a page.

    `owner` / `by_when` / `action` render as one bold, assertive line right
    after the title — "<b>Action:</b> ... — <owner>, by <when>" — so an item
    never reads as vague background noise with no one on the hook for it.

    `status` renders as a bold colored tag inline with the title —
    "[BLOCKED] Renew the MSA" — so Open / Completed / Blocked / Waiting on
    someone / Needs confirmation / New discussion point are visually
    distinct at a glance rather than uniform bullets the reader has to parse
    one by one.
    """
    block = []
    if first and header is not None:
        style = {
            "alert": styles["section_alert"],
            "success": styles["section_success"],
        }.get(header_tone, styles["section"])
        block.append(Paragraph(esc(header), style))
    if title or status:
        tag = ""
        if status:
            tag = '<font color="%s"><b>[%s]</b></font> ' % (
                _status_color(status), esc(str(status).upper()))
        block.append(Paragraph("%s%s" % (tag, esc(title) if title else ""),
                                styles["item_title"]))
    if action or owner or by_when:
        segments = []
        if action:
            segments.append(esc(action))
        if owner:
            segments.append("Owner: %s" % esc(owner))
        if by_when:
            segments.append("By: %s" % esc(by_when))
        block.append(Paragraph(" &nbsp;·&nbsp; ".join(segments), styles["action"]))
    for line in (lines or []):
        if line is None or str(line).strip() == "":
            continue
        block.append(Paragraph(esc(line), styles["body"]))
    if fix:
        block.append(Paragraph(
            '<font color="#B5431F"><b>Suggested fix:</b></font> %s' % esc(fix),
            styles["fix"],
        ))
    if source:
        block.append(Paragraph(esc(source), styles["source"]))
    if block:
        story.append(KeepTogether(block))


def _section_flowables(styles, heading):
    """A section heading as flowables: a hairline rule, then the label.

    The rule is what makes the page scannable — it gives every section a
    visible top edge, so the eye finds "What was promised" without reading
    the paragraph above it.

    Returned rather than appended so `doc_item` can glue a heading into the
    same KeepTogether as its first item. Appending it separately let a
    heading strand itself at the foot of a page with its content overleaf —
    which looks exactly like a document that ran out of content.
    """
    return [
        Spacer(1, num(11)),
        HRule(0, space=num(0), color=RULE),
        Paragraph(esc(heading), styles["doc_section"]),
    ]


def doc_section(story, styles, heading):
    """Append a section heading. Use for a section with no first item to
    glue to — an empty state, or a block of prose."""
    story.extend(_section_flowables(styles, heading))


def doc_item(story, styles, text_width, label=None, cite=None, title=None,
            lines=None, status=None, owner=None, by_when=None, related=None,
            heading=None, first=False, preformatted=False):
    """One call-prep item on the two-column reading grid.

    Left gutter: the label (who owes it, whose objection, which attendee) and
    the source citation. Right column: title, status tag, substance — set to
    a ~70-character measure.

    Falls back to full-width single-column rendering for an unusually long
    item, because a single table row cannot split across a page break and an
    over-tall row would abort the render. Long items are rare by design (the
    skill caps every field's length) but the fallback means a verbose payload
    degrades to the old layout instead of failing.
    """
    head = _section_flowables(styles, heading) if (first and heading) else []

    right = []
    tag = ""
    if status:
        tag = '<font color="%s"><b>[%s]</b></font> ' % (
            _status_color(status), esc(str(status).upper()))
    if title:
        right.append(Paragraph("%s%s" % (tag, esc(title)),
                               styles["doc_item_title"]))
        tag = ""            # consumed by the title line
    body_lines = [l for l in (lines or [])
                  if l is not None and str(l).strip() != ""]
    for n, line in enumerate(body_lines):
        # A status tag with no title rides on the first body line rather than
        # sitting alone above it, where it read as an orphaned label.
        prefix = tag if (n == 0 and tag) else ""
        # `preformatted` means the caller already escaped the text and added
        # its own inline markup (a bold action line, a coloured fix line).
        # Escaping it again would print the tags as literal characters.
        text = str(line) if preformatted else esc(line)
        right.append(Paragraph("%s%s" % (prefix, text), styles["doc_body"]))
    if tag and not body_lines:
        right.append(Paragraph(tag, styles["doc_body"]))
    trailer = [x for x in (
        ("Owner: %s" % owner) if owner else None,
        ("By: %s" % by_when) if by_when else None,
        ("Raised by: %s" % related) if related else None,
    ) if x]
    if trailer:
        right.append(Paragraph(
            " &nbsp;·&nbsp; ".join(esc(t) for t in trailer), styles["doc_cite"]))
    if not right:
        # An item with no column content is still an item: its heading and
        # gutter label must render, or an entire required section can vanish
        # from the PDF while the run exits 0 — the exact "silently skipped
        # heading" failure the format contract exists to prevent. Emit what
        # exists, with a placeholder so the gap is visible, not invisible.
        placeholder = [Paragraph("—", styles["doc_body"])]
    else:
        placeholder = None

    left = []
    if label:
        left.append(Paragraph(esc(label), styles["doc_label"]))
    for c in ([cite] if isinstance(cite, str) else (cite or [])):
        if c is None or str(c).strip() == "":
            continue
        left.append(Paragraph(esc(c), styles["doc_cite"]))

    if placeholder is not None:
        if not (head or left):
            return
        right = placeholder

    # Guard: one table row cannot split, so anything likely to run past a
    # page goes full width instead.
    bulk = sum(len(str(x)) for x in (lines or [])) + len(str(title or ""))
    if bulk > 900:
        # Label and body still travel together — splitting them let a page
        # break land between a citation and the claim it belongs to. The
        # heading rides along too, so it can never strand itself.
        story.append(KeepTogether(head + left + right))
        return

    grid = Table(
        [[left or "", right]],
        colWidths=[num(DOC_GUTTER), num(text_width)],
    )
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), num(DOC_GAP)),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), num(1)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), num(7)),
    ]))
    story.append(KeepTogether(head + [grid]))


def empty_state(story, styles, text):
    story.append(Paragraph(esc(text), styles["empty"]))


# --------------------------------------------------------------------------
# KIND 1 — daily brief
# --------------------------------------------------------------------------
class ContentVolumeError(Exception):
    """Raised when no legitimate layout gets a document inside its page range.

    Deliberately not recoverable inside the renderer. Padding a thin document
    with a blank trailing page, or shrinking an over-long one to unreadable
    type, are both worse than telling the caller to fix the content — and a
    blank trailing page is precisely the "scattered pages" defect this file
    exists to kill.
    """


def render_daily_brief(data, path):
    """The daily brief, on the same reading grid as every other document.

    It used to set its body across the full 6.8in measure with orange section
    headings, while call prep used a 4.95in column and quiet headings with
    hairline rules — two visual languages from one plugin, which read as two
    different products arriving in the same inbox. Both now share the grid,
    the type and the section treatment; only the content differs.
    """
    styles = build_styles()
    doc = _doc(path, MARGIN, data.get("title") or "Daily brief")
    width = num(PAGE_W - 2 * MARGIN)
    text_w = num(width - DOC_GUTTER)
    story = []

    # --- Masthead. Small, fixed-height, so the first real section always
    # --- begins on page 1. No CondPageBreak, no oversized KeepTogether:
    # --- those caused the blank first page.
    title = data.get("title") or "Daily Brief"
    story.append(Paragraph(esc(title), styles["doc_title"]))
    story.append(Paragraph(esc(data.get("headline") or "Clear day"),
                           styles["doc_item_title"]))
    story.append(Spacer(1, num(5)))
    story.append(HRule(width, space=num(6)))

    # --- Stat strip, same treatment as call prep's snapshot: one borderless
    # --- row of label:value cells rather than a pipe-delimited sentence.
    stats = data.get("stats") or {}
    if isinstance(stats, dict) and stats:
        cells = ["%s: %s" % (k, v) for k, v in stats.items()]
    elif stats:
        cells = [str(stats)]
    else:
        cells = []
    if cells:
        row = [Paragraph(esc(c), styles["meta"]) for c in cells]
        strip = Table([row], colWidths=[num(width / len(row))] * len(row))
        strip.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), num(6)),
            ("TOPPADDING", (0, 0), (-1, -1), num(4)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), num(6)),
        ]))
        story.append(strip)

    # --- Timeline spans the full measure: it is a picture of the day, not
    # --- prose, so the reading column does not apply to it.
    meetings = data.get("meetings") or []
    if meetings:
        story.append(Spacer(1, num(4)))
        story.append(Timeline(meetings, doc.width))
        story.append(Spacer(1, num(2)))

    # --- Today's meetings: time in the gutter, what and who in the column.
    if meetings:
        for i, mt in enumerate(meetings):
            label = mt.get("label") or mt.get("title") or ""
            # Split "9:15 – 9:35 am — Daily dev sync" so the time rides the
            # gutter and the subject gets the column, which is what makes the
            # list scannable by time.
            # Matched on a LEADING TIME, not on a dash: a bare
            # partition("—") duplicated the whole label whenever the
            # separator was missing or written as an en dash — and the
            # skill's own example uses an en dash inside the time range, so
            # the two are easy to confuse. No leading time → the label is
            # the title and the gutter stays empty; never force a subject
            # into a 1.75in gutter.
            m = re.match(
                r"^\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
                r"(?:\s*[-\u2013\u2014]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)"
                r"\s*[-\u2013\u2014]\s*(.+)$", label, re.I)
            when, what = (m.group(1), m.group(2)) if m else ("", label)
            lines = [x for x in (mt.get("who"), mt.get("format")) if x]
            doc_item(story, styles, text_w,
                     label=(when.strip() or None),
                     title=(what.strip() or label),
                     lines=lines,
                     heading="Today's meetings", first=(i == 0))
    else:
        doc_section(story, styles, "Today's meetings")
        empty_state(story, styles, "No meetings on the calendar today.")

    blocks = [
        ("Conflicts", data.get("conflicts") or [],
         "No scheduling conflicts today."),
        ("Due today & overdue", data.get("due_today") or [],
         "Nothing due today and nothing overdue."),
        ("Worth double-checking", data.get("worth_double_checking") or [],
         "No coverage gaps to flag."),
        ("Needs attention", data.get("needs_attention") or [],
         "Nothing waiting on you."),
        ("Resolved", data.get("resolved") or [],
         "Nothing closed out since yesterday."),
    ]

    for heading, items, empty_text in blocks:
        if not items:
            doc_section(story, styles, heading)
            empty_state(story, styles, empty_text)
            continue
        for i, it in enumerate(items):
            if isinstance(it, str):
                it = {"body": it}
            lines = []
            if it.get("action"):
                # The action is the point of the item, so it leads the column
                # in bold rather than trailing the body.
                lines.append("<b>%s</b>" % esc(str(it["action"])))
            for key in ("body", "detail", "meta"):
                if it.get(key):
                    lines.append(esc(str(it[key])))
            if it.get("fix"):
                lines.append('<font color="%s"><b>Suggested fix:</b></font> %s'
                             % (ALERT_BOLD_HEX, esc(str(it["fix"]))))
            # Owner rides the gutter with the citation — the same slot call
            # prep uses for "who owes this".
            doc_item(story, styles, text_w,
                     label=it.get("owner"),
                     cite=[it.get("by_when"), it.get("source")],
                     title=it.get("title"),
                     lines=lines,
                     status=it.get("status"),
                     heading=heading, first=(i == 0),
                     preformatted=True)

    sources = data.get("sources") or []
    if sources:
        doc_section(story, styles, "Sources")
        i = 0
        for src in sources:
            # The descriptive label IS the link. Printing the raw URL beside
            # it spent a line on something nobody reads and made the section
            # the longest on the page.
            if isinstance(src, dict):
                label = str(src.get("label") or "").strip()
                url = _clean_url(src.get("url"))
                if not label:
                    continue
                text = ('<link href="%s" color="%s">%s</link>'
                        % (esc(url), INFO_HEX, esc(label))) if url else esc(label)
            else:
                label = str(src or "").strip()
                if not label:
                    continue
                text = esc(label)
            i += 1
            story.append(Paragraph("%d. %s" % (i, text), styles["doc_cite"]))

    doc.build(
        story,
        canvasmaker=lambda *a, **kw: NumberedCanvas(
            *a, suppress_single_page_footer=True, **kw),
    )

    # A page ceiling, which this document never had -- on a busy day it simply
    # grew, and a five-page "daily brief" is a report nobody reads at 6am.
    # Reported as a content problem, because that is what it is: the remedy is
    # to cut items, never to shrink type.
    pages = _page_count(path)
    if pages > DAILY_BRIEF_MAX_PAGES:
        _discard(path)
        raise ContentVolumeError(
            "daily brief runs to %d pages, over the %d-page ceiling. Cut "
            "CONTENT, never type: keep every meeting and every real conflict "
            "(those are the brief), then take 'Due today & overdue' to what "
            "is genuinely due or late, 'Needs attention' to the asks that "
            "actually need the reader, and 'Resolved' to the items they were "
            "worried about. One line per item, no restating a title in its "
            "action. Aim for %d pages, then render again."
            % (pages, DAILY_BRIEF_MAX_PAGES, DAILY_BRIEF_MAX_PAGES))
    return path



# --------------------------------------------------------------------------
# Compact components for the 2-page briefings.
# --------------------------------------------------------------------------
# The briefings were running to five and six pages because every fact got its
# own grid row with a heading above it. These three components carry the same
# information in a fraction of the vertical space: a label/value strip, a
# real table, and a one-line semantic bullet. Nothing here shrinks type --
# the saving is structural.

def _discard(path):
    """Delete a rejected render so nothing downstream can attach it."""
    try:
        os.remove(path)
    except OSError:
        pass


def _clean_url(url):
    """Return a usable http(s) URL, or None. Never repairs, never invents.

    A malformed or non-http link rendered as an <a href> is a link that looks
    clickable and is not, which is worse than plain text.
    """
    u = str(url or "").strip()
    if not u or " " in u:
        return None
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    if "." not in u.split("//", 1)[-1].split("/", 1)[0]:
        return None
    return u


def glance_strip(styles, width, pairs, cols=3):
    """Label-over-value cells, wrapped into rows of `cols`.

    Replaces a stack of one-line grid rows: six facts that cost six rows and
    six headings now cost two rows and no headings.
    """
    pairs = [(k, v) for k, v in pairs if v]
    if not pairs:
        return []
    out = []
    for i in range(0, len(pairs), cols):
        chunk = pairs[i:i + cols]
        row = []
        for label, value in chunk:
            row.append([Paragraph(esc(str(label)).upper(), styles["glance_label"]),
                        Paragraph(esc(str(value)), styles["glance_value"])])
        # Pad the final row so column widths stay identical between rows.
        while len(row) < cols:
            row.append([])
        t = Table([row], colWidths=[num(width / cols)] * cols)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), num(8)),
            ("TOPPADDING", (0, 0), (-1, -1), num(2)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), num(5)),
        ]))
        out.append(t)
    return out


def compact_table(styles, width, headers, rows, weights=None, zebra=True):
    """A real table: header row, hairline rules, optional zebra banding.

    Every cell is a Paragraph so long text wraps instead of overflowing.
    `rows` entries are lists of (text, style_key) or plain strings.
    """
    if not rows:
        return []
    n = len(headers)
    weights = weights or [1.0] * n
    total = float(sum(weights)) or 1.0
    widths = [num(width * (w / total)) for w in weights]

    data = [[Paragraph(esc(str(h)).upper(), styles["cell_head"]) for h in headers]]
    for r in rows:
        cells = []
        for c in r[:n]:
            if isinstance(c, (list, tuple)):
                text, key = (list(c) + ["cell"])[:2]
            else:
                text, key = c, "cell"
            cells.append(Paragraph(esc("" if text is None else str(text)),
                                   styles.get(key, styles["cell"])))
        while len(cells) < n:
            cells.append(Paragraph("", styles["cell"]))
        data.append(cells)

    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), num(5)),
        ("RIGHTPADDING", (0, 0), (-1, -1), num(5)),
        ("TOPPADDING", (0, 0), (-1, -1), num(3)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), num(4)),
        ("LINEBELOW", (0, 0), (-1, 0), num(0.6), RULE),
        ("LINEBELOW", (0, 1), (-1, -2), num(0.4), RULE),
    ]
    if zebra:
        # Band every other BODY row, counting from the first one. Counting
        # from the header banded row 2 of a 2-row table and left row 1 white.
        for i in range(1, len(data)):
            if (i - 1) % 2 == 1:
                style.append(("BACKGROUND", (0, i), (-1, i), TABLE_BG))
    t.setStyle(TableStyle(style))
    return [t]


def sem_bullets(styles, items, role=None):
    """One line per item, a coloured marker where the role is meaningful."""
    out = []
    for it in items:
        if isinstance(it, str):
            it = {"body": it}
        text = it.get("body") or it.get("title") or ""
        if not str(text).strip():
            continue
        r = it.get("role") or role
        colour = SEMANTIC.get(r, (INK_TERTIARY, INK_TERTIARY_HEX, None))[1]
        src = it.get("source")
        tail = ('  <font size="7" color="%s">%s</font>'
                % (INK_TERTIARY_HEX, esc(str(src)))) if src else ""
        title = it.get("title")
        head = ("<b>%s</b> " % esc(str(title))) if title and it.get("body") else ""
        out.append(Paragraph(
            '<font color="%s">\u25aa</font>&nbsp;&nbsp;%s%s%s'
            % (colour, head, esc(str(text)), tail), styles["bullet"]))
    return out

# --------------------------------------------------------------------------
# KIND 2 — call prep (1-2 pages, compact executive briefing)
# --------------------------------------------------------------------------
def _call_prep_story(data, styles, width):
    """A 2-page executive briefing, in the order a person actually needs it.

    This replaced a fifteen-section dossier that ran to five and six pages.
    The old structure gave every fact its own grid row under its own heading,
    and repeated the call's basics in the header, the snapshot and again in
    the body -- so length grew with the amount of source material rather than
    with how much the reader needed.

    The order answers, in sequence: why is this call happening, who am I
    speaking with, what do I need to know, what should I accomplish, what
    should I ask, what could go wrong, who owes what, and where did all this
    come from. Nine sections, compact components, second-person headings.
    """
    story = []
    s = styles

    # ---- masthead: title plus the one-sentence reason this call exists ----
    story.append(Paragraph(esc(data.get("company") or "Call briefing"),
                           s["doc_title"]))
    if data.get("context"):
        story.append(Paragraph(esc(data["context"]), s["doc_item_title"]))
    if data.get("classification_note"):
        story.append(Paragraph(esc(data["classification_note"]), s["doc_cite"]))
    story.append(Spacer(1, num(4)))
    story.append(HRule(width, space=num(5)))

    # ---- 1. call at a glance: every basic fact, once, in two table rows ----
    story += glance_strip(s, width, [
        ("When", data.get("time")),
        ("Duration", data.get("duration")),
        ("Format", data.get("format")),
        ("Account owner", data.get("owner")),
        ("Stage", data.get("stage")),
        ("Last contact", data.get("last_contact")),
    ], cols=3)
    if data.get("desired_outcome"):
        story.append(AccentBox(Paragraph(
            "<b>Desired outcome.</b> " + esc(data["desired_outcome"]),
            s["objective"]), width))
        story.append(Spacer(1, num(3)))

    # ---- 2. who you'll be speaking with -- deliberately prominent ----
    att_rows = []
    for a in (data.get("attendees") or []):
        if isinstance(a, str):
            a = {"body": a}
        name = a.get("name") or "Name not established"
        if a.get("first_time"):
            name += "  (first time)"
        att_rows.append([
            (name, "cell_bold"),
            (" \u00b7 ".join([x for x in (a.get("title"), a.get("company")) if x])
             or "title not established", "cell_soft"),
            (a.get("body") or "", "cell"),
        ])
    story.append(Paragraph("Who you\u2019ll be speaking with", s["tight_section"]))
    if att_rows:
        story += compact_table(s, width, ["Person", "Role", "Why they matter"],
                               att_rows, weights=[1.05, 1.15, 2.0])
    else:
        story.append(Paragraph("Attendees could not be established.", s["empty"]))
        if data.get("absent_decision_maker"):
            story.append(Paragraph(esc(data["absent_decision_maker"]), s["doc_cite"]))

    # ---- 3. what you need to know before the call ----
    # A silently skipped heading reads as "nothing here" when it may mean
    # "never researched" -- shared §11 requires the heading plus a one-line
    # empty state. Sources is the documented exception.
    know = data.get("what_you_need_to_know") or []
    story.append(Paragraph("What you need to know before the call",
                           s["tight_section"]))
    if know:
        story += sem_bullets(s, know, role="info")
    else:
        story.append(Paragraph("Nothing on record.", s["empty"]))

    # ---- 4. what you should accomplish ----
    if data.get("objective"):
        story.append(Paragraph("What you should accomplish", s["tight_section"]))
        story.append(Paragraph(esc(data["objective"]), s["doc_body"]))

    # ---- 5. questions you should ask ----
    qs = data.get("questions") or []
    if qs:
        story.append(Paragraph("Questions you should ask", s["tight_section"]))
        for n, q in enumerate(qs, 1):
            story.append(Paragraph("<b>%d.</b>&nbsp;&nbsp;%s" % (n, esc(str(q))),
                                   s["bullet"]))

    # ---- 6. risks to watch -- objections and sensitivities, merged ----
    risks = data.get("risks") or []
    story.append(Paragraph("Risks to watch", s["tight_section"]))
    if risks:
        story += sem_bullets(s, risks, role="risk")
    else:
        story.append(Paragraph("None found in the research.", s["empty"]))

    # ---- 7. actions and owners -- one table, every commitment in it ----
    act_rows = []
    for a in (data.get("actions") or []):
        if isinstance(a, str):
            a = {"body": a}
        act_rows.append([
            (a.get("owner") or "", "cell_bold"),
            (a.get("body") or a.get("title") or "", "cell"),
            (a.get("by_when") or "", "cell_soft"),
            (a.get("status") or "", "cell_soft"),
        ])
    story.append(Paragraph("Actions &amp; owners", s["tight_section"]))
    if act_rows:
        story += compact_table(s, width, ["Owner", "Action", "By when", "Status"],
                               act_rows, weights=[0.85, 2.3, 0.7, 0.8])
    else:
        story.append(Paragraph("No open commitments on either side.", s["empty"]))

    # ---- 8. sources -- descriptive labels, real links only ----
    srcs = data.get("sources") or []
    if srcs:
        story.append(Paragraph("Sources", s["tight_section"]))
        # Number the rows actually kept. enumerate() over the raw list
        # consumed an index before a `continue`, so a dropped source left a
        # gap in the numbering (1. 3. 4.) and looked like a missing citation.
        i = 0
        for src in srcs:
            if isinstance(src, dict):
                label = str(src.get("label") or "").strip()
                url = _clean_url(src.get("url"))
            else:
                label, url = str(src or "").strip(), None
            if not label:
                continue
            i += 1
            if url:
                text = '%d. <a href="%s" color="%s">%s</a>' % (
                    i, esc(url), INFO_HEX, esc(label))
            else:
                text = "%d. %s" % (i, esc(label))
            story.append(Paragraph(text, s["doc_cite"]))

    return story

# The briefing is now a 1-2 page executive summary, not a dossier. One page
# is legitimate for a short call; two is the ceiling, and content is cut to
# fit rather than type shrunk to fit -- the fitting ladder below is allowed
# only a narrow band, and anything still over 2 pages is a content problem
# the accuracy gate reports as such.
CALL_PREP_MIN_PAGES = 1
CALL_PREP_TARGET_PAGES = 2
CALL_PREP_MAX_PAGES = 2


def render_call_prep(data, path):
    """One to two pages, two preferred, by deterministic layout fitting.

    Type size may move within a readable band to pull an outlier into range.
    Anything still outside it is a content-volume problem, not a layout one,
    and raises ContentVolumeError with actionable guidance.
    """
    width = num(PAGE_W - 2 * CALL_PREP_MARGIN)
    company = data.get("company") or "Account brief"

    def build_at(scale):
        styles = build_styles(scale)
        doc = _doc(path, CALL_PREP_MARGIN, company)
        doc.build(_call_prep_story(data, styles, width),
                  canvasmaker=lambda *a, **kw: NumberedCanvas(
                      *a, suppress_single_page_footer=True, **kw))
        return _page_count(path)

    # Try natural size first — most briefs land in range untouched, and
    # rescaling a document that already fits only makes it look odd.
    pages_at_1 = build_at(1.0)

    # A 2-page briefing whose second page carries three lines is the "one-line
    # content occupying a large block" defect, and the near-empty-page check
    # in verify() fails it as exit 4. If the content collapses onto a single
    # page within the readable band, it was only just spilling -- take the one
    # page. A genuinely full two-pager will not collapse, so it keeps its size.
    if pages_at_1 == 2:
        for scale in (0.97, 0.94):
            if build_at(scale) == 1:
                return path
        build_at(1.0)          # nothing collapsed it; restore natural size

    if CALL_PREP_MIN_PAGES <= pages_at_1 <= CALL_PREP_MAX_PAGES:
        return path

    seen = {1.0: pages_at_1}
    if pages_at_1 > CALL_PREP_MAX_PAGES:
        # A narrow band only. Past 0.94 the briefing stops being comfortable
        # to read at arm's length, and the requirement is explicit that type
        # size is not the lever -- content volume is.
        ladder = (0.97, 0.94)
    else:
        # One page is a legitimate outcome for a short call, so there is
        # nothing to open up. Never inflate type to manufacture a page 2.
        ladder = ()

    for scale in ladder:
        pages = build_at(scale)
        seen[scale] = pages
        if CALL_PREP_MIN_PAGES <= pages <= CALL_PREP_MAX_PAGES:
            return path

    best = min(seen.values())
    worst = max(seen.values())

    if best > CALL_PREP_MAX_PAGES:
        # Remove the over-length artefact. Leaving it on disk let §5's
        # "attach whatever rendered" path attach a document the gate had
        # just rejected.
        _discard(path)
        raise ContentVolumeError(
            "brief runs to %d pages, over the %d-page ceiling. This is a "
            "CONTENT problem, not a layout one, and the fix is to cut -- "
            "never to shrink type. In order: (1) 'What you need to know' to "
            "the 4 bullets that change how you run the call; (2) 'Risks to "
            "watch' to 3; (3) one line per attendee, 20 words, and drop any "
            "attendee whose relevance you could not establish; (4) Actions "
            "to those with a real owner -- an action nobody owns is not an "
            "action; (5) Sources to the 6 actually cited. If it does not "
            "help the reader prepare, decide, ask, act or follow up, it "
            "does not belong. Aim for %d pages, then render again."
            % (best, CALL_PREP_MAX_PAGES, CALL_PREP_TARGET_PAGES)
        )
    if worst < CALL_PREP_MIN_PAGES:
        raise ContentVolumeError(
            "brief rendered to %d pages, which should not be reachable with "
            "a 1-page floor. Treat it as a renderer defect, not a content "
            "one, and report it rather than padding. Target %d pages."
            % (worst, CALL_PREP_TARGET_PAGES)
        )
    raise ContentVolumeError(
        "could not land %d-%d pages across the readable size band (results: "
        "%s). Adjust the content and render again."
        % (CALL_PREP_MIN_PAGES, CALL_PREP_MAX_PAGES,
           ", ".join("%.2f->%dp" % (k, v) for k, v in sorted(seen.items())))
    )


# --------------------------------------------------------------------------
# KIND 3 — follow-ups summary
# --------------------------------------------------------------------------
def render_follow_ups(data, path):
    """DEPRECATED — kraken-follow-ups no longer renders or attaches anything.

    Its deliverable is a plain-text summary email plus the drafts themselves,
    which is also what makes it immune to a renderer or sandbox outage. This
    renderer and its format contract are kept only so an older stored
    scheduled-task prompt that still calls --kind follow_ups degrades to a
    working PDF instead of exit 2. Do not call it from new code.
    """
    styles = build_styles()
    doc = _doc(path, MARGIN, data.get("title") or "Follow-ups")
    story = []

    story.append(Paragraph(esc(data.get("headline") or "Follow-ups ready for review"),
                           styles["headline"]))
    if data.get("lead"):
        story.append(Paragraph(esc(data["lead"]), styles["stat"]))
    story.append(Spacer(1, num(4)))
    story.append(HRule(doc.width, space=num(4)))

    for heading, key in (("New today", "new_today"), ("Still open", "still_open")):
        groups = data.get(key) or {}
        if isinstance(groups, list):
            groups = {"": groups}
        if not any(groups.get(p) for p in ("High", "Medium", "Low", "")):
            section(story, styles, heading)
            empty_state(story, styles, "Nothing in this group.")
            continue
        section(story, styles, heading)
        for priority in ("High", "Medium", "Low", ""):
            items = groups.get(priority) or []
            for it in items:
                if isinstance(it, str):
                    it = {"title": it}
                label = it.get("title") or " — ".join(
                    [x for x in (it.get("company"), it.get("contact"),
                                 it.get("about")) if x])
                prefix = ("%s · " % priority) if priority else ""
                # status defaults per section: an item under "Still open"
                # that carries no explicit status is, by definition, still
                # open — an unsent draft aging toward escalation. "New
                # today" defaults to "New" since it wasn't seen before this
                # run. Either can be overridden (e.g. "Waiting on Kaleb",
                # "Blocked", "Needs confirmation").
                default_status = "Open" if heading == "Still open" else "New"
                add_item(story, styles,
                         title="%s%s" % (prefix, label),
                         lines=[it.get("reason"), it.get("body")],
                         source=it.get("source"),
                         status=it.get("status") or default_status)

    flagged = data.get("needs_your_input") or []
    if flagged:
        for i, it in enumerate(flagged):
            if isinstance(it, str):
                it = {"body": it}
            add_item(story, styles, title=it.get("title"), lines=[it.get("body")],
                     source=it.get("source"), status=it.get("status") or "Needs confirmation",
                     first=(i == 0), header="Needs your input", header_tone="alert")
    else:
        section(story, styles, "Needs your input", "alert")
        empty_state(story, styles, "Nothing flagged for your input this run.")

    if data.get("style_note"):
        section(story, styles, "Style corpus")
        story.append(Paragraph(esc(data["style_note"]), styles["body"]))

    doc.build(story, canvasmaker=lambda *a, **kw: NumberedCanvas(
        *a, suppress_single_page_footer=True, **kw))
    return path


# --------------------------------------------------------------------------
# FORMAT CONTRACT — the documented shape of each output, enforced.
# --------------------------------------------------------------------------
# Section ORDER is guaranteed structurally: each render_* function emits its
# sections in a fixed sequence, so order cannot drift. What a caller *can* get
# wrong is dropping a section, or shipping a brief with no objective. This
# checks for that before anything is rendered, so a malformed payload fails
# loudly instead of producing a plausible-looking but incomplete document.

class FormatError(Exception):
    """Payload does not match the documented format for its kind."""


# key -> whether it must also be non-empty
FORMAT_CONTRACT = {
    "daily_brief": {
        "required": {
            "headline": True,
            "stats": True,
            "meetings": False,
            "conflicts": False,
            "due_today": False,
            "worth_double_checking": False,
            "needs_attention": False,
            "resolved": False,
            "sources": False,
        },
        "note": (
            "Sections render in the fixed documented order: headline, stat "
            "line, timeline, Today's meetings, Conflicts, Due today & "
            "overdue, Worth double-checking, Needs attention, Resolved, "
            "Sources. Pass every key — an empty list renders its heading "
            "plus a one-line empty state (Sources renders nothing at all "
            "when empty, since it is a citation list, not a status "
            "section). Omitting a required key is a format error, because a "
            "silently missing section reads as 'nothing there' when it may "
            "mean 'never checked'. Every item in conflicts, due_today, "
            "worth_double_checking and needs_attention should carry action "
            "(an imperative one-line instruction), owner (a named person, "
            "never 'you' or 'team'), and by_when (a date or explicit "
            "deadline) — these render as one bold line under the title. An "
            "item with no owner and no by_when is the vague, unaccountable "
            "phrasing this contract exists to rule out. Any item may also "
            "carry status — one of Open / Completed / Blocked / Waiting on "
            "<name> / Needs confirmation / New — rendered as a bold colored "
            "tag on the title line; when status reflects a cross-channel "
            "check (e.g. resolved via Slack, not the channel the item first "
            "appeared in), say so in `source` so the check is visible, not "
            "just its conclusion. `sources` is an optional list of strings "
            "or {label, url} objects — a de-duplicated citation list (the "
            "threads, tickets, and events the brief actually drew on) "
            "rendered as a final numbered section, so every claim in the "
            "brief can be traced back to where it came from."
        ),
    },
    "call_prep": {
        "required": {
            # Masthead and the glance strip. `context` is the one sentence
            # saying why this call is happening -- the first question the
            # briefing has to answer.
            "company": True,
            "context": True,
            "time": True,
            "duration": False,
            "format": False,
            "owner": False,
            "stage": False,
            "last_contact": False,
            "classification_note": False,
            # People, deliberately prominent.
            "attendees": True,
            "absent_decision_maker": False,
            # Substance.
            "what_you_need_to_know": True,
            "objective": True,
            "desired_outcome": True,
            "questions": True,
            "risks": False,
            "actions": False,
            "sources": True,
        },
        "note": (
            "A 1-2 PAGE EXECUTIVE BRIEFING, not a dossier. Nine sections in "
            "this fixed order: masthead (company + context), call at a "
            "glance (time/duration/format/owner/stage/last_contact + "
            "desired_outcome), 'Who you'll be speaking with' (attendees "
            "table), 'What you need to know before the call' "
            "(what_you_need_to_know, at most 4 bullets), 'What you should "
            "accomplish' (objective), 'Questions you should ask' (4-6), "
            "'Risks to watch' (risks, at most 3), 'Actions & owners' "
            "(actions table), Sources. "
            "Length is controlled by CUTTING CONTENT, never by shrinking "
            "type: if it does not help the reader prepare, decide, ask, act "
            "or follow up, leave it out. "
            "Each attendee is {name, title, company, body} where body is ONE "
            "line, at most 20 words, on why that person matters -- plus "
            "optional first_time: true. Each actions entry is {owner, body, "
            "by_when, status}: the owner is a NAMED person ('you' and 'the "
            "team' are rejected), and an action nobody owns does not belong "
            "in the table. what_you_need_to_know and risks entries are "
            "{body, source, optional title}. Every questions entry is a "
            "question this account and this moment actually raise, "
            "unanswerable from the briefing itself. Sources carry a "
            "descriptive label and, where the connector returned one, a real "
            "http(s) url -- a malformed url is dropped rather than rendered "
            "as a dead link, and a url is never invented."
        )
    },
    "follow_ups": {
        "required": {
            "headline": True,
            "lead": True,
            "new_today": False,
            "still_open": False,
            "needs_your_input": False,
        },
        "note": (
            "Order is fixed: lead line, Still open (unsent drafts first, "
            "aged), New today, Needs your input. Pass new_today and "
            "still_open as objects keyed High/Medium/Low. Both may be empty, "
            "but both keys must be present — a missing still_open is how "
            "unsent drafts silently vanish from the report. Each item may "
            "carry status; still_open defaults to 'Open' and new_today to "
            "'New' when omitted, but override to Blocked / Waiting on "
            "<name> / Needs confirmation when that is the item's real state "
            "— e.g. a follow-up you cannot draft because the recipient "
            "address could not be verified is Needs confirmation, not Open."
        ),
    },
}


# --------------------------------------------------------------------------
# ACCURACY GATE — checks that used to live only in prose
# --------------------------------------------------------------------------
# Every rule below was documented in a skill as required and enforced by
# nothing, which is how owner/by_when shipped as a "format requirement" that
# was never once checked, and how a status could read "probably done" and
# render as an unrecognised grey tag.
#
# Two tiers, deliberately:
#
#   HARD (raises FormatError -> exit 6) for defects that make the document
#   wrong or misleading: a status outside the vocabulary, a Completed claim
#   with nothing behind it, an unaccountable actionable item, an owner of
#   "you". The caller fixes the payload and renders again.
#
#   WARN (printed to stderr, exit unchanged) for defects that make it
#   sloppier but still true: a related_to pointing at no real question, a
#   citation missing from Sources, a placeholder left in. Failing a whole
#   brief over a missing Sources row would lose the PDF to protect a
#   footnote, which is the wrong trade.

STATUS_VOCAB = (
    "open", "completed", "blocked", "waiting on",
    "needs confirmation", "new",
)

# "you", "team", "we" name nobody. A brief whose owner is "you" is exactly
# the vague, unaccountable phrasing a client called unusable.
BANNED_OWNERS = {
    "you", "your", "yourself", "team", "the team", "we", "us", "someone",
    "somebody", "tbd", "n/a", "na", "unknown", "-", "?",
}

# Whole words only. Without the trailing boundary this fired on "TODOS",
# "XXXL", "Placeholders were removed" and "tbaseline". The bracket form is a
# separate alternative because a \b cannot match before "[".
PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:tbd|tba|todo|fixme|xxx+|lorem ipsum|placeholder)\b"
    r"|\binsert\s+\w+\s+here\b"
    r"|\[[^\]]{1,40}\]\s*$)", re.I)

# Daily Brief's four actionable sections. Resolved is deliberately absent —
# those items are closed, so action/owner/by_when do not apply to them.
# Two pages, same as call prep. The brief is a morning scan, not a report.
DAILY_BRIEF_MAX_PAGES = 2

DAILY_BRIEF_ACTIONABLE = (
    "conflicts", "due_today", "worth_double_checking", "needs_attention",
)

# Per-field length limits for call prep, from its SKILL.md "Hard limits per
# field" table. Enforced in two tiers: over the limit warns, well over it
# fails — because a 27-word sentence where 25 were asked for is a nit, while
# a 60-word one is the flab the limits exist to stop. (words, sentences)
CALL_PREP_LIMITS = {
    "attendees":            {"body": (20, 1)},
    "what_you_need_to_know": {"body": (28, 2)},
    "risks":                {"body": (28, 2)},
    "actions":              {"body": (22, 1)},

}
# A field this far past its limit is a hard failure, not a warning.
HARD_OVERRUN = 1.6


def _norm_status(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _status_ok(value):
    """True only for the six statuses, optionally with a real tail.

    "Waiting on Dana" and "New discussion point" carry a tail, so a bare
    equality check is too strict — but a bare prefix check is far too loose
    (it accepted "openish" and "newsflash: nothing"), so the tail must begin
    at a word boundary. "Waiting on" with nobody named also fails, because
    §4 requires the person be named.
    """
    n = _norm_status(value)
    if not n:
        return False
    for v in STATUS_VOCAB:
        if v == "waiting on":
            # needs an actual name after it
            if n.startswith("waiting on ") and n[len("waiting on "):].strip():
                return True
            continue
        if n == v or n.startswith(v + " "):
            return True
    return False


def _items_of(data, key):
    """Yield (index, dict) for a section, tolerating bare strings and the
    High/Medium/Low grouping that follow-ups uses."""
    val = data.get(key)
    if isinstance(val, dict):                      # {High: [...], ...}
        # Every band, not only the three expected spellings — an unexpected
        # key used to skip the whole accuracy gate for those items silently.
        ordered = [b for b in ("High", "Medium", "Low") if b in val]
        ordered += [b for b in val if b not in ordered]
        for band in ordered:
            entries = val.get(band)
            if not isinstance(entries, (list, tuple)):
                continue
            for i, it in enumerate(entries):
                yield "%s.%s[%d]" % (key, band, i), (it if isinstance(it, dict)
                                                     else {"body": it})
        return
    for i, it in enumerate(val or []):
        yield "%s[%d]" % (key, i), (it if isinstance(it, dict) else {"body": it})


def accuracy_check(kind, data):
    """Return (hard_problems, warnings) for the payload.

    Deterministic and cheap — no model judgement, only rules a script can
    settle. Anything requiring judgement stays in the skill's own pre-send
    gate, where it belongs.
    """
    hard, warn = [], []

    status_sections = {
        "daily_brief": DAILY_BRIEF_ACTIONABLE + ("resolved",),
        "call_prep": ("actions",),
        "follow_ups": ("new_today", "still_open", "needs_your_input"),
    }.get(kind, ())

    # ---- status vocabulary, and Completed needs a trace ----
    for key in status_sections:
        for where, it in _items_of(data, key):
            if it.get("informational") is True:
                # A coverage note is a statement about the run. It carries no
                # status by design, so it must not be failed for lacking one.
                continue
            st = it.get("status")
            if st is not None and not _status_ok(st):
                hard.append(
                    "%s: status %r is not one of Open / Completed / Blocked / "
                    "Waiting on <name> / Needs confirmation / New — an "
                    "unrecognised status renders as an undifferentiated grey "
                    "tag and tells the reader nothing"
                    % (where, str(st)))
            if _norm_status(st).startswith("completed"):
                trace = (it.get("source") or "").strip() if isinstance(
                    it.get("source"), str) else it.get("source")
                if not trace:
                    hard.append(
                        "%s: status Completed with no `source` — nothing may "
                        "be marked done without a specific trace (a message, "
                        "a ticket state, a reaction). If there is no trace, "
                        "the status is Needs confirmation." % where)

    # ---- Daily Brief: every actionable item is accountable ----
    if kind == "daily_brief":
        for key in DAILY_BRIEF_ACTIONABLE:
            for where, it in _items_of(data, key):
                # A coverage note ("chat asks were not swept this run") is a
                # statement about the run, not a task: it has no owner and no
                # deadline, and inventing one to satisfy this gate would
                # break the no-fabrication rule. Such items pass
                # `informational: true` and are exempt from accountability —
                # but nothing else is.
                if it.get("informational") is True:
                    continue
                for field in ("action", "owner", "by_when"):
                    if _is_empty(it.get(field)):
                        hard.append(
                            "%s: missing `%s` — every item in Conflicts, Due "
                            "today & overdue, Worth double-checking and Needs "
                            "attention must state what to do, who owns it, and "
                            "by when. An item with no owner and no deadline is "
                            "the vague phrasing this contract exists to rule out."
                            % (where, field))
                owner = str(it.get("owner") or "").strip().lower().rstrip(".")
                if owner in BANNED_OWNERS:
                    hard.append(
                        "%s: owner %r names nobody — resolve a real person, or "
                        "default to the user. Never 'you' or 'team'."
                        % (where, it.get("owner")))
                if _is_empty(it.get("status")):
                    hard.append(
                        "%s: missing `status` — pass Open / Completed / Blocked "
                        "/ Waiting on <name> / Needs confirmation / New, "
                        "verified across channels rather than assumed."
                        % where)

    # ---- Call Prep: question count, and related_to must point somewhere real ----
    # An owner that names nobody is the same defect wherever it appears.
    for key in ("actions",):
        for where, it in _items_of(data, key):
            owner = str(it.get("owner") or "").strip().lower().rstrip(".")
            if owner and owner in BANNED_OWNERS:
                hard.append(
                    "%s: owner %r names nobody — name the person, or the named "
                    "function that holds it ('Acme Legal'). Never 'you', "
                    "'them' or a bare 'the team'."
                    % (where, it.get("owner")))

    if kind == "call_prep":
        # Ownership is explicit or the row does not belong. An action with no
        # owner is the thing the redesign exists to remove -- it reads as a
        # commitment while committing nobody.
        for where, it in _items_of(data, "actions"):
            if not str(it.get("owner") or "").strip():
                hard.append(
                    "%s: an action with no owner. Name the person who holds "
                    "it, or cut the row — an unowned action is not an action."
                    % where)

        # Bullet ceilings. These are the two sections that grow with the
        # amount of source material rather than with what the reader needs,
        # which is how the briefing reached six pages.
        for key, cap, label in (("what_you_need_to_know", 4,
                                 "'What you need to know' bullets"),
                                ("risks", 3, "'Risks to watch' bullets")):
            v = data.get(key)
            if isinstance(v, (list, tuple)) and len(v) > cap:
                hard.append(
                    "%s: %d %s — the format allows %d. Keep the ones that "
                    "change how the call is run; a briefing that lists "
                    "everything prioritises nothing."
                    % (key, len(v), label, cap))

        qs = data.get("questions") or []
        if isinstance(qs, (list, tuple)) and len(qs) > 6:
            hard.append(
                "questions: %d discovery questions — the format calls for 4-6. "
                "More than six is a list nobody works through on a 45-minute "
                "call; keep the sharpest six." % len(qs))
        # The 4-question floor is documented in three places and was enforced
        # in none, so a 2-question brief rendered clean.
        elif isinstance(qs, (list, tuple)) and len(qs) < 4:
            hard.append(
                "questions: %d discovery question(s) — the format calls for "
                "4-6. Fewer than four is not preparation; write questions "
                "this account and this moment actually raise, each one "
                "unanswerable from the brief itself." % len(qs))
        q_text = " ".join(str(q).lower() for q in qs)
        body_text = " ".join(
            str(it.get("title") or "") + " " + str(it.get("body") or "")
            for key in ("what_you_need_to_know", "risks", "actions")
            for _, it in _items_of(data, key)
        ).lower()
        for where, it in _items_of(data, "actions"):
            rel = str(it.get("related_to") or "").strip()
            if not rel:
                continue
            # A real related_to shares vocabulary with a question or the
            # situation text. Nothing in common means the link was invented,
            # which the skill explicitly forbids.
            words = [w for w in re.findall(r"[a-z]{4,}", rel.lower())]
            if words and not any(w in q_text or w in body_text for w in words):
                warn.append(
                    "%s: related_to %r matches no discovery question or "
                    "discussion point in this brief — omit it rather than "
                    "forcing a connection that isn't real." % (where, rel))

    # ---- call prep: per-field length limits ----
    if kind == "call_prep":
        for key, fields in CALL_PREP_LIMITS.items():
            for where, it in _items_of(data, key):
                for field, (max_words, max_sents) in fields.items():
                    v = it.get(field)
                    if not isinstance(v, str) or not v.strip():
                        continue
                    words = len(v.split())
                    sents = len([x for x in re.split(r"[.!?]+(?:\s|$)", v)
                                 if x.strip()])
                    over = []
                    if words > max_words:
                        over.append("%d words (limit %d)" % (words, max_words))
                    if sents > max_sents:
                        over.append("%d sentences (limit %d)"
                                    % (sents, max_sents))
                    if not over:
                        continue
                    msg = ("%s.%s: %s — the brief is read in the five minutes "
                           "before a call; cut words, not facts"
                           % (where, field, " and ".join(over)))
                    if (words > max_words * HARD_OVERRUN
                            or sents > max_sents + 1):
                        hard.append(msg)
                    else:
                        warn.append(msg)

        # Top-level strings are not item sections, so CALL_PREP_LIMITS never
        # reached them — yet their limits are documented. Check them here.
        for field, (max_words, max_sents) in (("context", (28, 1)),
                                              ("objective", (25, 1)),
                                              ("desired_outcome", (22, 1))):
            v = data.get(field)
            if not isinstance(v, str) or not v.strip():
                continue
            words = len(v.split())
            sents = len([x for x in re.split(r"[.!?]+(?:\s|$)", v) if x.strip()])
            over = []
            if words > max_words:
                over.append("%d words (limit %d)" % (words, max_words))
            if sents > max_sents:
                over.append("%d sentences (limit %d)" % (sents, max_sents))
            if over:
                msg = "%s: %s — cut words, not facts" % (field, " and ".join(over))
                if words > max_words * HARD_OVERRUN or sents > max_sents + 1:
                    hard.append(msg)
                else:
                    warn.append(msg)

        qs = data.get("questions") or []
        for i, q in enumerate(qs):
            if isinstance(q, str) and len(q.split()) > 20:
                warn.append("questions[%d]: %d words (limit 20) — a question "
                            "nobody can hold in their head is not asked"
                            % (i, len(q.split())))

    # ---- every cited source should appear in the Sources list ----
    src_blob = ""
    for src in (data.get("sources") or []):
        if isinstance(src, dict):
            # str() rather than "" defaults: a null label or url used to
            # raise TypeError out of the gate, which escaped uncaught and,
            # in batch mode, took every remaining job down with it.
            src_blob += "%s %s " % (src.get("label") or "", src.get("url") or "")
        else:
            src_blob += "%s " % (src if src is not None else "")
    src_blob = src_blob.lower()
    if src_blob.strip():
        seen = set()
        for key in set(status_sections) | {"attendees", "risks",
                                           "what_you_need_to_know"}:
            for where, it in _items_of(data, key):
                cite = str(it.get("source") or "").strip()
                if not cite or cite.lower() in seen:
                    continue
                seen.add(cite.lower())
                # Heuristic, deliberately: a citation with no digit in it is
                # treated as a generic locator ("CRM contact record", "chat
                # profile") that names a connector rather than a retrievable
                # record, so it has nothing to appear in Sources AS. This is a
                # proxy, not a rule — it lets "Jira ACME-QA" through
                # unchecked and does check "CRM record, last activity 3 days
                # ago" — which is why it warns rather than fails.
                if not re.search(r"\d", cite):
                    continue
                toks = [w for w in re.findall(r"[a-z0-9#-]{4,}", cite.lower())]
                if toks and not any(t in src_blob for t in toks):
                    warn.append(
                        "%s: cited %r but nothing like it is in `sources` — a "
                        "claim the reader cannot trace back is the gap the "
                        "Sources section exists to close." % (where, cite))

    # ---- placeholders left in ----
    for key in set(status_sections) | {"attendees", "risks", "actions",
                                       "questions", "what_you_need_to_know",
                                       "meetings"}:
        for where, it in _items_of(data, key):
            for field in ("title", "body", "action", "owner", "by_when"):
                v = it.get(field)
                if isinstance(v, str) and PLACEHOLDER_RE.search(v):
                    warn.append("%s.%s: looks like placeholder text (%r)"
                                % (where, field, v[:60]))
    for field in ("objective", "context", "desired_outcome", "headline", "lead"):
        v = data.get(field)
        if isinstance(v, str) and PLACEHOLDER_RE.search(v):
            warn.append("%s: looks like placeholder text (%r)" % (field, v[:60]))

    return hard, warn


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def check_format(kind, data):
    """Raise FormatError if the payload breaks its kind's documented contract."""
    contract = FORMAT_CONTRACT.get(kind)
    if not contract:
        return
    if not isinstance(data, dict):
        raise FormatError("payload must be a JSON object, got %s"
                          % type(data).__name__)

    missing, empty = [], []
    for key, must_fill in contract["required"].items():
        if key not in data:
            missing.append(key)
        elif must_fill and _is_empty(data[key]):
            empty.append(key)

    problems = []
    if missing:
        problems.append("missing key(s): %s" % ", ".join(sorted(missing)))
    if empty:
        problems.append("present but empty, and must carry content: %s"
                        % ", ".join(sorted(empty)))

    # Call prep needs enough questions to actually run a call.
    if kind == "call_prep":
        qs = data.get("questions") or []
        if isinstance(qs, str):
            # A bare string would be enumerated one numbered line per
            # CHARACTER, which renders as nonsense rather than failing.
            problems.append(
                "questions must be a LIST of 4-6 question strings, not one "
                "string")
            qs = []
        if isinstance(qs, (list, tuple)) and 0 < len(qs) < 4:
            problems.append(
                "only %d discovery question(s) — the format calls for 4-6, "
                "aim for 5" % len(qs))

    # The accuracy gate (see accuracy_check) runs in the same pass: a status
    # outside the vocabulary or an unaccountable item is a format defect in
    # exactly the same sense as a missing key.
    # A bug in the gate itself must never cost the document. Anything the
    # gate cannot parse is reported as a warning and the render proceeds —
    # the format contract above has already caught the structural defects.
    try:
        hard, warnings = accuracy_check(kind, data)
    except Exception as exc:
        hard, warnings = [], ["accuracy gate could not run (%s: %s)"
                              % (type(exc).__name__, exc)]
    problems.extend(hard)

    for w in warnings:
        print("ACCURACY WARNING: %s" % w, file=sys.stderr)

    if problems:
        raise FormatError(
            "%s payload does not match the documented format.\n  - %s\n\n%s"
            % (kind, "\n  - ".join(problems), contract["note"]))


# --------------------------------------------------------------------------
# MARKDOWN BACKUP — a plain-text copy of the same payload, always written
# alongside the PDF. Exists because an attachment can silently fail to reach
# the user (a sandbox/mail-tool quirk, not a rendering bug) with no PDF-level
# signal that anything went wrong. The markdown carries the same content, so
# a run is never a total loss even when the PDF never arrives.
# --------------------------------------------------------------------------
def _md_bits(*parts):
    return " · ".join(str(p) for p in parts if p not in (None, ""))


def _md_item(it, heading=None):
    if isinstance(it, str):
        it = {"body": it}
    lines = []
    prefix = "### " if heading is None else "- "
    title = it.get("title")
    # status renders as a "[STATUS]" tag on the title line, mirroring the
    # PDF's colored tag — never folded in as an ordinary body line.
    status = it.get("status")
    head_line = _md_bits(
        ("[%s]" % str(status).upper()) if status else None, title
    ) if (title or status) else None
    action_bits = _md_bits(
        it.get("action"),
        ("Owner: %s" % it["owner"]) if it.get("owner") else None,
        ("By: %s" % it["by_when"]) if it.get("by_when") else None,
    )
    if head_line:
        lines.append("%s**%s**" % (prefix, head_line))
    if action_bits:
        lines.append("  **%s**" % action_bits if heading is None else "  - **%s**" % action_bits)
    for key in ("body", "detail", "meta"):
        if it.get(key):
            lines.append("  %s" % it[key] if heading is None else "  - %s" % it[key])
    if it.get("fix"):
        lines.append("  Suggested fix: %s" % it["fix"])
    if it.get("source"):
        lines.append("  Source: %s" % it["source"])
    return "\n".join(lines)


def _md_cell(value):
    """A table cell that cannot break the row it sits in.

    The markdown file is what shared §5 attaches when the PDF fails, so a
    pipe in a connector-supplied name silently turning a 3-column row into a
    5-column one is a defect that reaches the user.
    """
    t = str(value or "")
    t = t.replace("\\", "\\\\").replace("|", "\\|")
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def _md_text(value):
    """Inline markdown text: neutralise the characters that form markup."""
    t = str(value or "")
    for ch in ("\\", "`", "*", "_", "[", "]", "<", ">"):
        t = t.replace(ch, "\\" + ch)
    return t


def _md_sources(sources):
    """Sources, rendered exactly as the PDF renders them.

    The daily brief's markdown printed the raw URL next to its label, kept
    rows the PDF drops, and never validated a URL -- three ways for the
    backup to say something different from the document it backs up.
    """
    out = []
    if not sources:
        return out
    out.append("## Sources")
    i = 0
    for src in sources:
        if isinstance(src, dict):
            label = str(src.get("label") or "").strip()
            url = _clean_url(src.get("url"))
        else:
            label, url = str(src or "").strip(), None
        if not label:
            continue
        i += 1
        label = _md_text(label)
        out.append("%d. %s" % (i, "[%s](%s)" % (label, url) if url else label))
    out.append("")
    return out


def to_markdown(kind, data):
    """Plain-text rendition of `data` for the given `kind`. Mirrors the PDF's
    section order and content exactly — it is a backup, not a summary."""
    data = data or {}
    out = []

    if kind == "daily_brief":
        out.append("# %s" % (data.get("title") or "Daily brief"))
        out.append("")
        out.append("**%s**" % (data.get("headline") or "Clear day"))
        stats = data.get("stats") or {}
        if isinstance(stats, dict) and stats:
            out.append(_md_bits(*("%s: %s" % (k, v) for k, v in stats.items())))
        elif stats:
            out.append(str(stats))
        out.append("")
        meetings = data.get("meetings") or []
        out.append("## Today's meetings")
        if meetings:
            for mt in meetings:
                out.append("- **%s** — %s" % (
                    mt.get("label") or mt.get("title") or "Meeting",
                    _md_bits(mt.get("who"), mt.get("format")),
                ))
        else:
            out.append("No meetings on the calendar today.")
        out.append("")
        for heading, items, empty_text in (
            ("Conflicts", data.get("conflicts") or [], "No scheduling conflicts today."),
            ("Due today & overdue", data.get("due_today") or [], "Nothing due today and nothing overdue."),
            ("Worth double-checking", data.get("worth_double_checking") or [], "No coverage gaps to flag."),
            ("Needs attention", data.get("needs_attention") or [], "Nothing waiting on you."),
            ("Resolved", data.get("resolved") or [], "Nothing closed out since yesterday."),
        ):
            out.append("## %s" % heading)
            if items:
                for it in items:
                    out.append(_md_item(it))
            else:
                out.append(empty_text)
            out.append("")
        out += _md_sources(data.get("sources") or [])

    elif kind == "call_prep":
        # Same nine sections, same order as the PDF. The backup exists to be
        # read when the PDF did not arrive, so a different shape would be its
        # own defect.
        out.append("# %s" % (data.get("company") or "Call briefing"))
        if data.get("context"):
            out.append("")
            out.append("**%s**" % data["context"])
        if data.get("classification_note"):
            out.append("")
            out.append("_%s_" % data["classification_note"])
        out.append("")
        glance = [(k, data.get(v)) for k, v in (
            ("When", "time"), ("Duration", "duration"), ("Format", "format"),
            ("Account owner", "owner"), ("Stage", "stage"),
            ("Last contact", "last_contact"))]
        glance = [(k, v) for k, v in glance if v]
        if glance:
            out.append(" | ".join("**%s:** %s" % (k, v) for k, v in glance))
            out.append("")
        if data.get("desired_outcome"):
            out.append("**Desired outcome.** %s" % data["desired_outcome"])
            out.append("")

        atts = data.get("attendees") or []
        out.append("## Who you'll be speaking with")
        out.append("")
        if not atts:
            out.append("Attendees could not be established.")
            out.append("")
        if atts:
            out.append("| Person | Role | Why they matter |")
            out.append("|---|---|---|")
            for a in atts:
                if isinstance(a, str):
                    a = {"body": a}
                name = a.get("name") or "Name not established"
                if a.get("first_time"):
                    name += " (first time)"
                role = " · ".join([x for x in (a.get("title"), a.get("company")) if x]) \
                    or "title not established"
                out.append("| %s | %s | %s |" % (_md_cell(name), _md_cell(role),
                                                 _md_cell(a.get("body"))))
            out.append("")
            if data.get("absent_decision_maker"):
                out.append("_%s_" % data["absent_decision_maker"])
                out.append("")

        def _bullets(heading, key, empty):
            items = data.get(key) or []
            out.append("## %s" % heading)
            if not items:
                out.append(empty)
                out.append("")
                return
            for it in items:
                if isinstance(it, str):
                    it = {"body": it}
                title = ("**%s** " % it["title"]) if it.get("title") else ""
                src = ("  _(%s)_" % it["source"]) if it.get("source") else ""
                out.append("- %s%s%s" % (title, it.get("body") or "", src))
            out.append("")

        _bullets("What you need to know before the call", "what_you_need_to_know",
                 "Nothing on record.")

        if data.get("objective"):
            out.append("## What you should accomplish")
            out.append(data["objective"])
            out.append("")
        qs = data.get("questions") or []
        if qs:
            out.append("## Questions you should ask")
            for n, q in enumerate(qs, 1):
                out.append("%d. %s" % (n, q))
            out.append("")
        _bullets("Risks to watch", "risks", "None found in the research.")
        acts = data.get("actions") or []
        out.append("## Actions & owners")
        out.append("")
        if not acts:
            out.append("No open commitments on either side.")
            out.append("")
        if acts:
            out.append("| Owner | Action | By when | Status |")
            out.append("|---|---|---|---|")
            for a in acts:
                if isinstance(a, str):
                    a = {"body": a}
                out.append("| %s | %s | %s | %s |" % (
                    _md_cell(a.get("owner")),
                    _md_cell(a.get("body") or a.get("title")),
                    _md_cell(a.get("by_when")), _md_cell(a.get("status"))))
            out.append("")
        out += _md_sources(data.get("sources") or [])
    elif kind == "follow_ups":
        out.append("# %s" % (data.get("title") or "Follow-ups"))
        out.append("")
        out.append("**%s**" % (data.get("headline") or ""))
        if data.get("lead"):
            out.append(data["lead"])
        out.append("")
        for heading, key in (("Still open", "still_open"), ("New today", "new_today")):
            groups = data.get(key) or {}
            out.append("## %s" % heading)
            any_items = False
            if isinstance(groups, dict):
                default_status = "Open" if heading == "Still open" else "New"
                for priority in ("High", "Medium", "Low"):
                    for it in (groups.get(priority) or []):
                        any_items = True
                        if isinstance(it, str):
                            it = {"body": it}
                        title = it.get("title") or "Item"
                        status_tag = str(it.get("status") or default_status).upper()
                        detail = _md_bits(it.get("body"), it.get("detail"), it.get("meta"))
                        head = "- **[%s] [%s] %s**" % (priority, status_tag, title)
                        out.append("%s — %s" % (head, detail) if detail else head)
                        if it.get("source"):
                            out.append("  Source: %s" % it["source"])
            if not any_items:
                out.append("Nothing here this run.")
            out.append("")
        flagged = data.get("needs_your_input") or []
        out.append("## Needs your input")
        if flagged:
            for it in flagged:
                out.append(_md_item(it, heading="Needs your input"))
        else:
            out.append("Nothing flagged for your input this run.")
        if data.get("style_note"):
            out.append("")
            out.append("## Style corpus")
            out.append(data["style_note"])

    else:
        out.append("```json")
        out.append(json.dumps(data, indent=2, default=str))
        out.append("```")

    return "\n".join(out).strip() + "\n"


def write_markdown(kind, data, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(kind, data))
    return path


# --------------------------------------------------------------------------
# VERIFICATION — the caller never has to rasterize or eyeball anything.
# --------------------------------------------------------------------------
def _page_count(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        # Fall back to counting page objects in the raw file.
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
            # One read, and a boundary so /Type /Pages (the page TREE, of
            # which there is one) is not counted as a page. Calling read()
            # twice made the subtrahend always zero.
            return max(1, len(re.findall(rb"/Type\s*/Page(?![s/\w])", blob)))
        except Exception:
            return -1


def verify(path, expect_pages=None, min_ink_ratio=0.004):
    """Return (ok, [problems]). Catches every failure mode from the bad build."""
    problems = []

    if not os.path.exists(path):
        return False, ["file was not written"]
    size = os.path.getsize(path)
    if size < 800:
        problems.append("file is only %d bytes — almost certainly truncated" % size)

    try:
        from pypdf import PdfReader
    except ImportError:
        return (not problems), problems or ["pypdf unavailable — size check only"]

    warnings = io.StringIO()
    try:
        reader = PdfReader(path)
        pages = reader.pages
    except Exception as exc:  # pragma: no cover
        return False, ["PDF could not be parsed: %s" % exc]

    total = len(pages)
    if total == 0:
        return False, ["PDF has no pages"]
    if expect_pages is not None and total != expect_pages:
        problems.append("expected %d pages, got %d" % (expect_pages, total))

    footers = 0
    for i, page in enumerate(pages, 1):
        # 1) Content stream must actually decode. This is the check that would
        #    have caught "invalid distance too far back" before the client saw it.
        try:
            raw = page.get_contents()
            data = raw.get_data() if raw is not None else b""
            if not data:
                problems.append("page %d has an empty content stream" % i)
                continue
        except Exception as exc:
            problems.append("page %d content stream failed to decode: %s" % (i, exc))
            continue

        # 2) No scientific-notation numbers, which the PDF parser reads as
        #    bogus operators.
        if re.search(rb"\d[eE][-+]?\d", data):
            problems.append(
                "page %d content stream contains a scientific-notation number "
                "(invalid PDF syntax)" % i)

        # 2b) No run-together numbers such as ".52.1572" or "420.18778.96" —
        #     two decimal points in one token. This is what the shipped bad
        #     build emitted, and it silently zeroes the coordinate.
        if re.search(rb"(?<![\w/])\.?\d*\.\d+\.\d", data):
            problems.append(
                "page %d content stream contains a malformed number with two "
                "decimal points (coordinates written without separators)" % i)

        # 3) Balanced graphics state — an unmatched q/Q corrupts later pages.
        q = len(re.findall(rb"(?m)^\s*q\s*$", data))
        Q = len(re.findall(rb"(?m)^\s*Q\s*$", data))
        if q != Q:
            problems.append("page %d has unbalanced graphics state (q=%d, Q=%d)" % (i, q, Q))

        # 4) Real extractable text, and enough of it that the page is not the
        #    near-blank page 1 from the bad build.
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            problems.append("page %d text extraction failed: %s" % (i, exc))
            text = ""
        if len(text.strip()) < 40:
            problems.append(
                "page %d is effectively blank (%d characters of text)"
                % (i, len(text.strip())))
        if re.search(r"Page\s+\d+\s+of\s+\d+", text):
            footers += 1

    # 5) Every page carries a footer — including page 1 and the last page.
    if total > 1 and footers != total:
        problems.append(
            "footer missing on %d of %d pages (found %d)"
            % (total - footers, total, footers))

    # 6) Ink coverage, if a rasterizer is available: catches a page that has
    #    text objects but draws almost nothing (the empty-looking page 1).
    try:
        import statistics

        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        inks = []
        for i in range(len(doc)):
            bitmap = doc[i].render(scale=0.6).to_numpy()
            if bitmap.ndim == 3:
                gray = bitmap[..., :3].mean(axis=2)
            else:
                gray = bitmap
            inks.append(float((gray < 240).mean()))
        doc.close()

        for i, ink in enumerate(inks, 1):
            if ink < min_ink_ratio:
                problems.append(
                    "page %d is visually near-empty (%.3f%% ink coverage)"
                    % (i, ink * 100))

        # Relative check — this is the one that catches the defect the client
        # reported. The bad build's page 1 held a headline and a stat line, so
        # it passed both the character count and the absolute ink floor, yet
        # sat two-thirds empty next to its neighbours. Any page except the
        # last that carries under a third of the median ink is a layout
        # failure: content that should have started there got pushed onward.
        if len(inks) > 2:
            others = statistics.median(inks[1:])
            for i, ink in enumerate(inks[:-1], 1):
                peers = statistics.median([v for j, v in enumerate(inks, 1) if j != i])
                if peers > 0 and ink < 0.33 * peers:
                    problems.append(
                        "page %d is mostly empty (%.2f%% ink vs %.2f%% median "
                        "on other pages) — content that belongs here was pushed "
                        "to a later page"
                        % (i, ink * 100, peers * 100))
            del others
    except ImportError:
        pass
    except Exception:
        pass

    warnings.close()
    return (len(problems) == 0), problems


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
RENDERERS = {
    "daily_brief": render_daily_brief,
    "call_prep": render_call_prep,
    "follow_ups": render_follow_ups,
}


def run_batch(manifest_path):
    """Render many PDFs in ONE process.

    Importing reportlab costs roughly half a second, so a call-prep night with
    eight briefs previously paid that eight times over — plus eight process
    starts — for no reason. A batch renders them all in one interpreter.

    Manifest: a JSON list of {"kind":..., "in":..., "out":...} jobs, or an
    object with a "jobs" key holding that list.
    """
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        print("INPUT ERROR: manifest: %s" % exc, file=sys.stderr)
        return 2

    jobs = manifest.get("jobs") if isinstance(manifest, dict) else manifest
    if not isinstance(jobs, list) or not jobs:
        print("INPUT ERROR: manifest must be a non-empty list of jobs",
              file=sys.stderr)
        return 2

    failures = 0
    for i, job in enumerate(jobs, 1):
        kind = (job or {}).get("kind")
        infile = (job or {}).get("in")
        outfile = (job or {}).get("out")
        mdfile = (job or {}).get("md")
        label = outfile or "job %d" % i

        if kind not in RENDERERS or not infile or not outfile:
            print("  FAIL %s — job needs valid kind, in and out" % label,
                  file=sys.stderr)
            failures += 1
            continue

        try:
            with open(infile, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print("  FAIL %s — payload: %s" % (label, exc), file=sys.stderr)
            failures += 1
            continue

        try:
            check_format(kind, data)
        except FormatError as exc:
            print("  FAIL %s — FORMAT: %s" % (label, exc), file=sys.stderr)
            failures += 1
            continue

        out_dir = os.path.dirname(os.path.abspath(outfile))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # Markdown backup ALWAYS written, even if a "md" path wasn't given —
        # defaults to the PDF path with .md in place of .pdf, so a sandbox
        # attach failure never means the run's content is unrecoverable.
        md_target = mdfile or (os.path.splitext(outfile)[0] + ".md")
        try:
            write_markdown(kind, data, md_target)
        except Exception as exc:
            print("  WARN %s — markdown backup failed: %s" % (label, exc), file=sys.stderr)

        try:
            RENDERERS[kind](data, outfile)
        except ContentVolumeError as exc:
            print("  FAIL %s — DOES NOT FIT: %s" % (label, exc), file=sys.stderr)
            failures += 1
            continue
        except Exception as exc:
            print("  FAIL %s — RENDER: %s" % (label, exc), file=sys.stderr)
            failures += 1
            continue

        expect = None
        pages = _page_count(outfile)
        ok, problems = verify(outfile, expect_pages=expect)
        if kind == "call_prep" and not (
                CALL_PREP_MIN_PAGES <= pages <= CALL_PREP_MAX_PAGES):
            problems.append("call prep must be %d-%d pages, got %d"
                            % (CALL_PREP_MIN_PAGES, CALL_PREP_MAX_PAGES, pages))
            ok = False

        if ok:
            print("  OK   %s — %d page(s) — markdown backup: %s"
                  % (label, pages, md_target))
        else:
            print("  FAIL %s — VERIFY: %s" % (label, "; ".join(problems)),
                  file=sys.stderr)
            failures += 1

    total = len(jobs)
    print("batch: %d/%d rendered and verified" % (total - failures, total))
    if failures:
        print("batch had %d failure(s) — fix those payloads and re-run just "
              "those jobs" % failures, file=sys.stderr)
        return 7
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a Kraken Productivity skill PDF.")
    ap.add_argument("--batch", dest="batch", default=None,
                    help="JSON manifest of {kind,in,out} jobs — renders every "
                         "PDF in one process. Use this whenever there is more "
                         "than one PDF to build.")
    ap.add_argument("--kind", choices=sorted(RENDERERS))
    ap.add_argument("--in", dest="infile",
                    help="JSON payload path, or - for stdin")
    ap.add_argument("--out", dest="outfile")
    ap.add_argument("--md-out", dest="mdfile", default=None,
                    help="markdown backup path — defaults to --out with .md "
                         "in place of .pdf, and is ALWAYS written (this is "
                         "the resilience fix for an attachment that silently "
                         "never reaches the user)")
    ap.add_argument("--expect-pages", type=int, default=None,
                    help="assert an exact page count. Diagnostics only: "
                         "passing it REPLACES call prep's 2-page ceiling "
                         "check with this exact-count check, so never pass "
                         "it in a real run.")
    ap.add_argument("--skip-format-check", action="store_true",
                    help="bypass the documented-format contract AND the accuracy "
                         "gate (diagnostics only — never in a real run)")
    args = ap.parse_args(argv)

    if args.batch:
        return run_batch(args.batch)

    missing = [n for n, v in (("--kind", args.kind), ("--in", args.infile),
                              ("--out", args.outfile)) if not v]
    if missing:
        print("INPUT ERROR: %s required (or use --batch)"
              % ", ".join(missing), file=sys.stderr)
        return 2

    try:
        if args.infile == "-":
            data = json.load(sys.stdin)
        else:
            with open(args.infile, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    except (OSError, ValueError) as exc:
        print("INPUT ERROR: %s" % exc, file=sys.stderr)
        return 2

    out_dir = os.path.dirname(os.path.abspath(args.outfile))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if not args.skip_format_check:
        try:
            check_format(args.kind, data)
        except FormatError as exc:
            print("FORMAT ERROR: %s" % exc, file=sys.stderr)
            return 6

    md_target = args.mdfile or (os.path.splitext(args.outfile)[0] + ".md")
    try:
        write_markdown(args.kind, data, md_target)
    except Exception as exc:
        print("WARN: markdown backup failed: %s" % exc, file=sys.stderr)

    try:
        RENDERERS[args.kind](data, args.outfile)
    except ContentVolumeError as exc:
        # Not a crash — the layout is fine, the content volume is wrong. Say so
        # plainly so the caller edits the payload instead of retrying blindly.
        print("CONTENT DOES NOT FIT: %s" % exc, file=sys.stderr)
        return 5
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("RENDER FAILED: %s" % exc, file=sys.stderr)
        return 3

    expect = args.expect_pages
    ok, problems = verify(args.outfile, expect_pages=expect)
    pages = _page_count(args.outfile)

    # Call prep has a page RANGE rather than a fixed count.
    if args.kind == "call_prep" and args.expect_pages is None:
        if not (CALL_PREP_MIN_PAGES <= pages <= CALL_PREP_MAX_PAGES):
            problems.append(
                "call prep must be %d-%d pages (target %d), got %d"
                % (CALL_PREP_MIN_PAGES, CALL_PREP_MAX_PAGES,
                   CALL_PREP_TARGET_PAGES, pages))
            ok = False

    if not ok:
        print("VERIFY FAILED for %s (%d pages):" % (args.outfile, pages), file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 4

    print("OK %s — %d page(s), %d bytes, all checks passed — markdown "
          "backup: %s" % (args.outfile, pages, os.path.getsize(args.outfile), md_target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
