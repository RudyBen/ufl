

#from ufl.core.expr import Expr
from ufl.expr import Expr

from ufl.common import camel2underscore

# Make UFL type coercion available under the as_ufl name
#as_ufl = Expr._ufl_coerce_


def get_base_attr(cls, name):
    "Return first non-None attribute of given name among base classes."
    for base in cls.mro():
        if hasattr(base, name):
            attr = getattr(base, name)
            if attr is not None:
                return attr
    return None


def ufl_type(is_abstract=False,
             is_terminal=None,
             is_scalar=False,
             is_shaping=False,
             num_ops=None,
             wraps_type=None,
             unop=None,
             binop=None,
             rbinop=None,
             ):
    """This decorator is to be applied to every subclass in the UFL Expr hierarchy.

    This decorator contains a number of checks that are
    intended to enforce uniform behaviour across UFL types.

    The rationale behind the checks and the meaning of the
    optional arguments should be sufficiently documented
    in the source code below.
    """

    def _ufl_type_decorator_(cls):

        # An abstract class cannot be instantiated and does not need all properties specified
        cls._ufl_is_abstract_ = is_abstract


        # Check that the first base classes up to Expr are other UFL types
        for base in cls.mro():
            if base is Expr:
                break
            if not issubclass(base, Expr) and base._ufl_is_abstract_:
                msg = "Base class {0.__name__} of class {1.__name__} is not an abstract subclass of {2.__name__}."
                raise TypeError(msg.format(base, cls, Expr))


        # Check if type has __slots__ or is marked as exception with _ufl_noslots_
        if "_ufl_noslots_" not in cls.__dict__:
            if "__slots__" not in cls.__dict__:
                msg = "Class {0.__name__} is missing the __slots__ attribute and is not marked with _ufl_noslots_."
                raise TypeError(msg.format(cls))

            # Check base classes for __slots__ as well, skipping object which is the last one
            for base in cls.mro()[1:-1]:
                if "__slots__" not in base.__dict__:
                    msg = "Class {0.__name__} is has a base class {1.__name__} with __slots__ missing."
                    raise TypeError(msg.format(cls, base))


        # Type is a shaping operation, e.g. indexing, slicing, transposing, not introducing new computation.
        cls._ufl_is_shaping_ = is_shaping


        # Check if type implements the required methods
        """ # TODO
        if not is_abstract:
            for attr in Expr._ufl_required_methods_:
                if not hasattr(cls, attr):
                    msg = "Class {0.__name__} has no {1} method."
                    raise TypeError(msg.format(cls, attr))
                elif not callable(getattr(cls, attr)):
                    msg = "Required method {1} of class {0.__name__} is not callable."
                    raise TypeError(msg.format(cls, attr))
        """

        # Check if type implements the required properties
        """ # TODO
        if not is_abstract:
            for attr in Expr._ufl_required_properties_:
                if not hasattr(cls, attr):
                    msg = "Class {0.__name__} has no {1} property."
                    raise TypeError(msg.format(cls, attr))
                elif callable(getattr(cls, attr)):
                    msg = "Required property {1} of class {0.__name__} is a callable method."
                    raise TypeError(msg.format(cls, attr))
        """

        # Assign the class object itself.
        # Makes it possible to do type(f)._ufl_class_ and be sure you get
        # the actual UFL class instead of a subclass from another library.
        cls._ufl_class_ = cls
        Expr._ufl_all_classes_.append(cls)


        # Assign a handler function name.
        # This is used for initial detection of multifunction handlers
        cls._ufl_handler_name_ = camel2underscore(cls.__name__)
        Expr._ufl_all_handler_names_.add(cls._ufl_handler_name_)


        # Assign an integer type code.
        # This is used for fast lookup into multifunction handler tables
        cls._ufl_typecode_ = Expr._ufl_num_typecodes_
        Expr._ufl_num_typecodes_ += 1


        # Attach builtin type wrappers to Expr
        """ # TODO
        if wraps_type is not None:
            if not isinstance(wraps_type, type):
                msg = "Expecting a type, not a {0.__name__} for the wraps_type argument in definition of {1.__name__}."
                raise TypeError(msg.format(type(wraps_type), cls))

            def _ufl_as_type_(value):
                return cls(value)
            as_type_name = "_ufl_as_{0}_".format(wraps_type.__name__)
            setattr(Expr, as_type_name, staticmethod(_ufl_as_type_))
        """


        # Attach special function to Expr.
        # Avoids the circular dependency problem of making
        # Expr.__foo__ return a Foo that is a subclass of Expr.
        """ # TODO
        if unop:
            def _ufl_expr_unop_(self):
                return cls(self)
            setattr(Expr, unop, _ufl_expr_unop_)
        if binop:
            def _ufl_expr_binop_(self, other):
                return cls(self, other)
            setattr(Expr, binop, _ufl_expr_binop_)
        if rbinop:
            def _ufl_expr_rbinop_(self, other):
                return cls(other, self)
            setattr(Expr, rbinop, _ufl_expr_rbinop_)
        """


        # Get trait is_terminal.
        # It's faster to use expr._ufl_is_terminal_ than to use isinstance(expr, Terminal)
        auto_is_terminal = get_base_attr(cls, "_ufl_is_terminal_")
        if is_terminal is None and auto_is_terminal is None:
            msg = "Class {0.__name__} has not specified the is_terminal trait. Did you forget to inherit from Terminal or Operator?"
            raise TypeError(msg.format(cls))
        elif auto_is_terminal is None:
            auto_is_terminal = is_terminal
        elif is_terminal is not None and (auto_is_terminal != is_terminal):
            msg = "Conflicting given and automatic 'is_terminal' trait for class {0.__name__}. Check if you meant to inherit from Terminal or Operator."
            raise TypeError(msg.format(cls))
        cls._ufl_is_terminal_ = auto_is_terminal


        # Simplify implementation of purely scalar types
        cls._ufl_is_scalar_ = is_scalar

        if not is_scalar:
            # Scalar? Then we can simplify the implementation of tensor properties by attaching them here.
            cls.ufl_shape = ()
            cls.ufl_free_indices = ()
            cls.ufl_index_dimensions = ()


        # Require num_ops to be set for non-abstract classes if it cannot be determined automatically
        auto_num_ops = num_ops

        # Determine from other args
        if auto_num_ops is None:
            if cls._ufl_is_terminal_:
                auto_num_ops = 0
            elif unop:
                auto_num_ops = 1
            elif binop or rbinop:
                auto_num_ops = 2

        # Determine from base class
        if auto_num_ops is None:
            auto_num_ops = get_base_attr(cls, "_ufl_num_ops_")

        cls._ufl_num_ops_ = auto_num_ops


        # Add to collection of language operators.
        # This collection is used later to populate the official language namespace.
        if not is_abstract and hasattr(cls, "_ufl_function_"):
            cls._ufl_function_.__func__.__doc__ = cls.__doc__
            Expr._ufl_language_operators_[cls._ufl_handler_name_] = cls._ufl_function_


        # Append space for counting object creation and destriction of this this type.
        Expr._ufl_obj_init_counts_.append(0)
        Expr._ufl_obj_del_counts_.append(0)


        # Consistency checks
        assert Expr._ufl_num_typecodes_ == len(Expr._ufl_all_handler_names_)
        assert Expr._ufl_num_typecodes_ == len(Expr._ufl_all_classes_)
        assert Expr._ufl_num_typecodes_ == len(Expr._ufl_obj_init_counts_)
        assert Expr._ufl_num_typecodes_ == len(Expr._ufl_obj_del_counts_)

        if not is_abstract:
            # Check that non-abstract types always specify num_ops
            if cls._ufl_num_ops_ is None:
                msg = "Class {0.__name__} has not specified num_ops."
                raise TypeError(msg.format(cls))

            # Check that num_ops has the right type
            if not (isinstance(cls._ufl_num_ops_, int) or cls._ufl_num_ops_ == "varying"):
                msg = 'Class {0.__name__} has invalid num_ops value {1} (integer or "varying").'
                raise TypeError(msg.format(cls, cls._ufl_num_ops_))

        # Check that num_ops is not set to nonzero for a terminal
        if cls._ufl_is_terminal_ and cls._ufl_num_ops_ != 0:
            msg = "Class {0.__name__} has num_ops > 0 but is terminal."
            raise TypeError(msg.format(cls))

        # Not scalar? Then check that we do not have a scalar base class (this works recursively).
        if not is_scalar:
            if get_base_attr(cls, "_ufl_is_scalar_"):
                msg = "Non-scalar class {0.__name__} is has a scalar base class."
                raise TypeError(msg.format(cls))

        return cls

    return _ufl_type_decorator_