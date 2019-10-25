# This file is part of Optcom.
#
# Optcom is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Optcom is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Optcom.  If not, see <https://www.gnu.org/licenses/>.

""".. moduleauthor:: Sacha Medaer"""

from typing import Callable, List, Optional, overload, Union

import numpy as np
from nptyping import Array

import optcom.utils.constants as cst
import optcom.utils.utilities as util
from optcom.domain import Domain
from optcom.effects.abstract_effect import AbstractEffect
from optcom.effects.attenuation import Attenuation
from optcom.effects.dispersion import Dispersion
from optcom.equations.abstract_equation import AbstractEquation
from optcom.field import Field
from optcom.parameters.fiber.effective_area import EffectiveArea
from optcom.parameters.fiber.nl_coefficient import NLCoefficient
from optcom.parameters.fiber.nl_index import NLIndex


class AbstractNLSE(AbstractEquation):
    r"""Non linear Schrodinger equations.

    Represent the different effects in the NLSE as well as different
    types of NLSEs.

    """

    def __init__(self, alpha: Optional[Union[List[float], Callable]],
                 alpha_order: int,
                 beta: Optional[Union[List[float], Callable]],
                 beta_order: int, gamma: Optional[Union[float, Callable]],
                 core_radius: float, NA: Union[float, Callable], ATT: bool,
                 DISP: bool, medium: str) -> None:
        r"""
        Parameters
        ----------
        alpha :
            The derivatives of the attenuation coefficients.
            :math:`[km^{-1}, ps\cdot km^{-1}, ps^2\cdot km^{-1},
            ps^3\cdot km^{-1}, \ldots]` If a callable is provided,
            variable must be angular frequency. :math:`[ps^{-1}]`
        alpha_order :
            The order of alpha coefficients to take into account. (will
            be ignored if alpha values are provided - no file)
        beta :
            The derivatives of the propagation constant.
            :math:`[km^{-1}, ps\cdot km^{-1}, ps^2\cdot km^{-1},
            ps^3\cdot km^{-1}, \ldots]` If a callable is provided,
            variable must be angular frequency. :math:`[ps^{-1}]`
        beta_order :
            The order of beta coefficients to take into account. (will
            be ignored if beta values are provided - no file)
        gamma :
            The non linear coefficient.
            :math:`[rad\cdot W^{-1}\cdot km^{-1}]` If a callable is
            provided, variable must be angular frequency.
            :math:`[ps^{-1}]`
        core_radius :
            The radius of the core. :math:`[\mu m]`
        NA :
            The numerical aperture.
        ATT :
            If True, trigger the attenuation.
        DISP :
            If True, trigger the dispersion.
        medium :
            The main medium of the fiber.

        """
        super().__init__()
        self._medium: str = medium
        self._disp_ind: int = -1
        self._delays_effects: List[AbstractEffect] = []
        if (ATT):
            self._effects_lin.append(Attenuation(alpha, alpha_order,
                                                 skip_taylor=[1]))
            self._delays_effects.append(self._effects_lin[-1])
        if (DISP):
            self._effects_lin.append(Dispersion(beta, beta_order,
                                                start_taylor=2))
            self._disp_ind = len(self._effects_lin) - 1
            self._delays_effects.append(self._effects_lin[-1])
        self._gamma: Array[float]
        self._predict_gamma: Optional[Callable] = None
        if (gamma is not None):
            if (callable(gamma)):
                self._predict_gamma = gamma
            else:
                self._gamma = np.asarray(util.make_list(gamma))
        else:
            nl_index = NLIndex(medium)
            eff_area = EffectiveArea(core_radius, NA)
            self._predict_gamma = NLCoefficient(nl_index, eff_area)
    # ==================================================================
    @property
    def gamma(self):

        return self._gamma
    # ==================================================================
    def open(self, domain: Domain, *fields: List[Field]) -> None:
        super().open(domain, *fields)
        self._delays = np.zeros((len(self._center_omega), 0))
        if (self._predict_gamma is not None):
            self._gamma = self._predict_gamma(self._center_omega)
        else:
            if (len(self._center_omega) < len(self._gamma)):
                self._gamma = self._gamma[:len(self._center_omega)]
            else:
                for i in range(len(self._gamma), len(self._center_omega)):
                    self._gamma = np.hstack((self._gamma, self._gamma[-1]))
        print('gamma: ', self._gamma)
    # ==================================================================
    def set(self, waves: Array[cst.NPFT], h: float, x: float) -> None:
        """This function is called before each step of the computation.
        """
        # Perform change of variable T = t - \beta_1 z to ignore GV
        step = int(round(x/h))
        if (self._delays.size):
            to_add = self._delays[:,-1].reshape(-1,1)
        else:
            # Step should be mainly = 0 but can be other if shooting
            to_add = np.zeros((len(self._center_omega), step+1))
        if (self._delays.shape[1] <= step):
            self._delays = np.hstack((self._delays, to_add))
        #if (self._disp_ind != -1):  # if dispersion
        #    for i in range(len(waves)):
        #        beta = self._effects_lin[self._disp_ind][i]
        #        if (len(beta) > 1):  # if there is beta_1
        #            self._delays[i][-1] += beta[1] * h
        if (self._delays_effects):  # if dispersion
            for i in range(len(waves)):
                for effect in self._delays_effects:
                    delay_factors = effect[i]
                    #print('effect: ', len(delay_factors), effect)
                    if (len(delay_factors) > 1):
                    #    print('effect delaying ', effect)
                        self._delays[i][-1] += delay_factors[1] * h
    # ==================================================================
    def close(self, domain: Domain, *fields: List[Field]) -> None:
        # update the time array of each field with GV delay
        index = 0
        if (fields):
            for field_list in fields:
                for field in field_list:
                    field.add_delay(self._delays[index:index+len(field)][:,-1])
                    index += len(field)
        super().close(domain, *fields)
