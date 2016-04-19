"""This module contains the TactusTrackersGenerator class that can be configured
to generate complete hypothesis trackers for the playback of a case."""

import playback
import defaults
import hypothesis
import collections
import logging


class HypothesisTracker(hypothesis.HypothesisFromIndex):
    """Class that holds information of the hypothesis evolution.

    A hypothesis is defined as a rho and a delta values, where all tactus
    predictions are described as: rho + delta * k, for some integer k.

    The 'name' of the hypothesis is given by the two onset indexes used
    to originate the hypothesis. The 'beta' value is the first hypothesis.
    'corr' contains a list of Correction objects with information about
    each correction performed over the hypothesis. 'cur' is the current value
    of the hypothesis. 'confs' contains the evolution of the confidence for
    the hypothesis.

    The tracker also contains some convenience methods to work with the
    current hypothesis. The 'r' property gives as the current rho value,
    the 'd' property the current 'delta'. The 'proj' generates all
    tactus predictions by the hypothesis within range of a playback.

    The 'update' method allows us to correct the current hypothesis with
    a correction function and to update the confence status with a
    confidence function.
    """

    def __init__(self, start_idx, end_idx, onset_times):
        super(self.__class__, self).__init__(start_idx, end_idx, onset_times)
        self.beta = self.htuple
        self.onset_times = onset_times
        self.corr = []  # [(onset_idx, hypothesis_correction)]
        self.confs = []  # [(onset_idx, conf_value)]

    def update(self, ongoing_play, eval_f, corr_f):
        "Updates a hypothesis with new conf and applying corrections."
        correction = corr_f(self, ongoing_play)
        self.corr.append((ongoing_play.discovered_index, correction))
        self.htuple = correction.new_hypothesis()
        n_conf = eval_f(self, ongoing_play)
        self.confs.append((ongoing_play.discovered_index, n_conf))

    @property
    def cur(self):
        return self.htuple

    @property
    def conf(self):
        return self.confs[-1][1]

    def origin_onsets(self):
        return (self.beta[0], sum(self.beta))


class TactusHypothesisTracker():
    """Configurable class to generate hypothesis trackers
    for a case.

    Configuration includes:
        * an eval function that defines how to evaluate a hypothesis over
        certain Playback
        * a correction functions that produces a HypothesisCorrection for a
        hypothesis over a Playback
        * a similarity function that defines how similar are two hypothesis
        * a similarity_epsilon that defines the threshold for trimming
        * a maximun amount of hypothesis trackers to be kept. Only hypotheses
        best confidence are kept.

    When called on a set of onset_times it will generate a list of
    hypothesis trackers
    """

    logger = logging.getLogger('TactusHypothesisTracker')

    def __init__(self, eval_f, corr_f, sim_f, similarity_epsilon,
                 min_delta, max_delta, max_hypotheses):
        self.eval_f = eval_f
        self.corr_f = corr_f
        self.sim_f = sim_f
        self.similarity_epsilon = similarity_epsilon
        self.min_delta = min_delta
        self.max_delta = max_delta
        self.max_hypotheses = max_hypotheses

    def __call__(self, onset_times):
        self.logger.debug('Started tracking for onsets (%d) : %s',
                          len(onset_times), onset_times)
        ongoing_play = playback.OngoingPlayback(onset_times)
        hypothesis_trackers = []
        while ongoing_play.advance():
            n_hts = list(self._generate_new_hypothesis(ongoing_play))
            self.logger.debug('New step. %d hypothesis created', len(n_hts))

            hypothesis_trackers.extend(n_hts)

            for h in hypothesis_trackers:
                h.update(ongoing_play, self.eval_f, self.corr_f)

            kept_hs, trimmed_hs = self._trim_similar_hypotheses(
                hypothesis_trackers, ongoing_play)

            k_best_hs, other_hs = self._split_k_best_hypotheses(kept_hs)
            hypothesis_trackers = k_best_hs
            self.logger.debug('End of step. %d trackers remaining',
                              len(hypothesis_trackers))

        return dict([(ht.name, ht) for ht in hypothesis_trackers])

    def _generate_new_hypothesis(self, ongoing_play):
        "Generates new hypothesis trackers given discovered onset in playback."
        end_index = ongoing_play.discovered_index - 1
        for k in xrange(end_index):
            delta = (ongoing_play.onset_times[end_index] -
                     ongoing_play.onset_times[k])
            if self.min_delta <= delta and delta <= self.max_delta:
                yield HypothesisTracker(k, end_index,
                                        ongoing_play.onset_times)

    def _trim_similar_hypotheses(self, hts, ongoing_play):
        """Partitions new hypothesis into those that should be trimmed given
        a set of comparsion hypothesis.

        Assumes hypothesis trackers are sorted by when they were generated in
        hts.
        """
        trimmed_hs_data = []
        kept_hs = []
        remaining_hts = collections.deque(hts)
        while remaining_hts:
            ht = remaining_hts.popleft()
            n_remaining_hts = collections.deque()
            kept_hs.append(ht)
            while remaining_hts:
                n_ht = remaining_hts.popleft()
                s = self.sim_f(ht, n_ht, ongoing_play)
                if s > (1 - self.similarity_epsilon):
                    trimmed_hs_data.append((n_ht, ht))
                else:
                    n_remaining_hts.append(n_ht)

            remaining_hts = n_remaining_hts

        return (kept_hs, trimmed_hs_data)

    def _split_k_best_hypotheses(self, hts):
        """Splits hypotheses into the self.max_hypotheses best
        (according to confidence) and the rest.

        Both result list will be sorted in order of generation."""
        hts_info = [(-1 * ht.conf, idx) for idx, ht in enumerate(hts)]
        sorted_hts_info = sorted(hts_info)
        best_hts_idx = set([
            i for _, i in sorted_hts_info[:self.max_hypotheses]])
        best_k_hts = [ht for idx, ht in enumerate(hts)
                      if idx in best_hts_idx]
        other_hts = [ht for idx, ht in enumerate(hts)
                     if idx not in best_hts_idx]
        return best_k_hts, other_hts


def default_tht():
    'Returns a TactusHypothesisTracker with the default configuration'
    return TactusHypothesisTracker(**defaults.config)
