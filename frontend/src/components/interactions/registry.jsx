import RevealChests from './RevealChests';
import SystemScan from './SystemScan';
import SortTypes from './SortTypes';
import BuildStatement from './BuildStatement';
import ValueDial from './ValueDial';
import PredictOutput from './PredictOutput';
import TraceLoop from './TraceLoop';
import FixTheBug from './FixTheBug';

/**
 * Widget registry.
 *
 * Maps the `widget` key of an interaction JSON file to the component that
 * draws it. This is the only place the engine's data layer meets React —
 * a new interaction type means a component here plus a JSON file, and no
 * change to the backend or the .scene parser.
 *
 * Keys must stay in sync with config/widgets.json, which the backend reads
 * to warn about scenes referencing a widget the UI cannot render.
 *
 * Every widget receives:
 *   config    — the opaque `config` object from the interaction JSON
 *   onSolved  — call once the learner has genuinely completed the beat
 */
export const WIDGETS = {
  reveal_chests: RevealChests,
  system_scan: SystemScan,
  sort_types: SortTypes,
  build_statement: BuildStatement,
  value_dial: ValueDial,
  predict_output: PredictOutput,
  trace_loop: TraceLoop,
  fix_the_bug: FixTheBug,
};

export default WIDGETS;
