def open_aarontools(session, stream, file_name, format_name=None, coordsets=False):
    from AaronTools.fileIO import FileReader
    from SEQCROW.residue_collection import ResidueCollection
    from SEQCROW.managers import ADD_FILEREADER
    from warnings import warn

    if format_name == "Gaussian input file":
        fmt = "com"
    elif format_name == "Gaussian output file":
        fmt = "log"    
    elif format_name == "ORCA output file":
        fmt = "out"
    elif format_name == "Psi4 output file":
        fmt = "dat"
    elif format_name == "XYZ file":
        fmt = "xyz"
    elif format_name == "FCHK file":
        fmt = "fchk"
    elif format_name == "sqm output file":
        fmt = "sqmout"

    fr = FileReader((file_name, fmt, stream), just_geom=False, get_all=True)

    if hasattr(stream, "close") and callable(stream.close):
        stream.close()

    if fr.file_type == "dat":
        format_name = "Psi4 output file"
    elif fr.file_type == "out":
        format_name = "ORCA output file"

    try:
        geom = ResidueCollection(fr, refresh_ranks=False)
    except Exception as e:
        s = "could not open %s" % file_name
        if "error" in fr.other and fr.other["error"]:
            s += "\n%s contains an error (%s):\n%s" % (format_name, fr.other["error"], fr.other["error_msg"])
        
        session.logger.error(s)
        session.logger.error(repr(e))
        return [], "SEQCROW failed to open %s" % file_name

    structure = geom.get_chimera(session, coordsets=(fr.all_geom is not None and len(fr.all_geom) > 1), filereader=fr)
    #associate the AaronTools FileReader with each structure
    session.filereader_manager.triggers.activate_trigger(ADD_FILEREADER, ([structure], [fr]))

    if coordsets:
        from chimerax.std_commands.coordset_gui import CoordinateSetSlider
        from SEQCROW.tools import EnergyPlot
        
        if "energy" in fr.other:
            nrg_plot = EnergyPlot(session, structure, fr)
            if not nrg_plot.opened:
                warn("energy plot could not be opened\n" + \
                     "there might be a mismatch between energy entries and structure entries in %s" % file_name)
                nrg_plot.delete()
            else:
                slider = CoordinateSetSlider(session, structure)

                if len(fr.all_geom) > 1:
                    structure.active_coordset_id = structure.num_coordsets
                    if coordsets:
                        slider.set_slider(structure.num_coordsets)

    if format_name == "Gaussian input file":
        a_or_an = "a"
    elif format_name == "Gaussian output file":
        a_or_an = "a"    
    elif format_name == "ORCA output file":
        a_or_an = "an"
    elif format_name == "Psi4 output file":
        a_or_an = "a"
    elif format_name == "XYZ file":
        a_or_an = "an"
    elif format_name == "FCHK file":
        a_or_an = "an"
    elif format_name == "sqm output file":
        a_or_an = "an"
        
    status = "Opened %s as %s %s %s" % (file_name, a_or_an, format_name, "movie" if coordsets else "")

    structure.filename = file_name

    return [structure], status


def save_aarontools(session, path, format_name, **kwargs):
    """ 
    save XYZ file using AaronTools
    kwargs may be:
        comment - str
    """
    from SEQCROW.residue_collection import ResidueCollection
    from AaronTools.geometry import Geometry
    from chimerax.atomic import AtomicStructure
    
    accepted_kwargs = ['comment', 'models']
    unknown_kwargs = [kw for kw in kwargs if kw not in accepted_kwargs]
    if len(unknown_kwargs) > 0:
        raise RuntimeWarning("unrecognized keyword%s %s?" % ("s" if len(unknown_kwargs) > 1 else "", ", ".join(unknown_kwargs)))
    
    if 'models' in kwargs:
        models = kwargs['models']
    else:
        models = None
    
    if models is None:
        models = session.models.list(type=AtomicStructure)

    models = [m for m in models if isinstance(m, AtomicStructure)]
    
    if len(models) < 1:
        raise RuntimeError('nothing to save')
    
    res_cols = [ResidueCollection(model) for model in models]
    atoms = []
    for res in res_cols:
        atoms.extend(res.atoms)
        
    geom = Geometry(atoms)
    
    if 'comment' in kwargs:
        geom.comment = kwargs["comment"]
    
    geom.write(outfile=path)