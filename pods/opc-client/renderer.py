#!/usr/bin/env python

import time
import numpy
from effectlayer import GammaLayer
from playlist import Playlist
from fade import *


class Renderer:
    """
    Renders the selected routine in the currently active playlist. 
    (A "routine" is an effect layer or list of effect layers.)
    Performs smooth transitions when the active routine changes (either due to swapping 
    playlists or to advancing the selection in the current playlist).
    
    Also applies a gamma correction layer after everything else is rendered.
    """
    def __init__(self, playlists, activePlaylist=None, useFastFades=False, gamma=2.2):
        """
        playlists argument should be dictionary of playlist names : playlists.
        useFastFades uses fast fades instead of linear fades when advancing/swapping playlists
         (see fade class comments below)
        """        
        if not playlists:
            raise Exception("Can't define a renderer without any playlists")
        self.playlists = playlists
        
        # activePlaylist is the name of the first playlist to display. Can be
        # omitted if playlists only has one thing in it
        if activePlaylist:
            self.activePlaylist = activePlaylist
        else:
            if len(playlists.keys()) == 1:
                self.activePlaylist = playlists.keys()[0]
            else:
                raise Exception("Can't define multi-playlist renderer without specifying active playlist")
            
        # used when fading between playlists, to know what to return to when the fade is done
        self.nextPlaylist = None 
        
        self.useFastFades = useFastFades
        self.fade = None
        self.gammaLayer = GammaLayer(gamma)
        
    def _get(self, playlistKey):
        if playlistKey:
            return self.playlists[playlistKey]
        else:
            return None
        
    def _active(self):
        return self._get(self.activePlaylist)
        
    def _next(self):
        return self._get(self.nextPlaylist)
        
    def render(self, model, params, frame):
        if self.fade:
            self.fade.render(model, params, frame)
            if self.fade.done:
                # If the fade was to a new playlist, set that one to active
                if self.nextPlaylist:
                    self.activePlaylist = self.nextPlaylist
                    self.nextPlaylist = None
                self.fade = None
        elif self.activePlaylist:
            for layer in self._active().selection():
                layer.render(model, params, frame)
                # layer.safely_render(model, params, frame)
        self.gammaLayer.render(model, params, frame)
        
    def advanceCurrentPlaylist(self, fadeTime=1):
        """Advance selection within current playlist"""
        active = self._active()
        if active:
            selection = active.selection()
            active.advance()
            self.fade = LinearFade(selection, active.selection(), fadeTime)
        else:
            raise Exception("Can't advance playlist - no playlist is currently active")
        

    def _fadeTimeForTransition(self, playlist):
        return max([effect.transitionFadeTime for effect in playlist.selection()])


    def swapPlaylists(self, nextPlaylist, intermediatePlaylist=None, advanceAfterFadeOut=True, fadeTime=1):
        """Swap to a new playlist, either directly or by doing a two-step fade to an intermediate one first."""
        # TODO check for wonky behavior when one fade is set while another is still in progress
        
        active = self._active()
        self.nextPlaylist = nextPlaylist
        
        if self.useFastFades:
            self.fade = FastFade(active.selection(), self._next().selection(), fadeTime)
        else:
            if intermediatePlaylist:
                middle = self._get(intermediatePlaylist)
                self.fade = TwoStepLinearFade(active.selection(), middle.selection(), self._next().selection(), 0.25, self._fadeTimeForTransition(middle))
                if advanceAfterFadeOut:
                    middle.advance()
            else:
                self.fade = LinearFade(active.selection(), self._next().selection(), fadeTime)
        if advanceAfterFadeOut:
            active.advance()



