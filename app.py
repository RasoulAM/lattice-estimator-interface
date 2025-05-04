from flask import Flask, render_template, request, jsonify
import math # Import math module for power function
from lattice_estimator.estimator import * # Assuming 'estimator' and its distributions (Binary, Ternary, DiscreteGaussian) are available in your environment

# Create a Flask application instance
app = Flask(__name__)

# Define the route for the home page
@app.route('/')
def index():
    """Renders the main index.html page."""
    # This function will render the index.html file when the user visits the root URL.
    return render_template('index.html')

# Define the route for computation, accepting POST requests
@app.route('/compute', methods=['POST'])
def compute():
    """
    Receives parameters from the frontend, performs a computation,
    and returns the result as JSON. Handles 'q' or 'log_2 q' input
    and the secret key distribution type.
    """
    # Get data from the incoming POST request form.
    # request.form is a dictionary containing the form data sent from the frontend.
    n_str = request.form.get('n')
    q_value_str = request.form.get('q_value') # Get the value entered for q/logq
    q_type = request.form.get('q_type') # Get whether it's 'q' or 'logq'
    secret_key_dist_type = request.form.get('secret_key_dist') # Get the selected secret key distribution type
    sigma_e_str = request.form.get('sigma_e')
    sigma_s_str = request.form.get('sigma_s') # Get sigma_s, only used for DiscreteGaussian
    hamming_weight_str = request.form.get('hamming_weight')
    length_bound_str = request.form.get('length_bound')
    rough_str = request.form.get('rough') 

    problem = request.form.get('problem')
    try:
        n = int(n_str)
        q_value = float(q_value_str) # Convert the entered value to float
        if q_type == 'logq':
            # If input is log_2 q, calculate q = 2^(log_2 q)
            # math.pow(base, exponent) calculates base raised to the power of exponent
            q = math.pow(2, q_value)
        else: # Assume q_type is 'q' if not 'logq'
            # If input is q, use the value directly
            q = q_value
            # Ensure q is an integer if the type is 'q'. float.is_integer() checks if a float has no fractional part.
            if not q.is_integer():
                # If it's not an integer, raise a ValueError
                raise ValueError("If 'q' is selected, the value must be an integer.")
            # Convert q to an integer after validation
            q = int(q)

    except (ValueError, TypeError) as e:
        # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
        result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
    except Exception as e:
        # Catch any other potential unexpected errors during computation
        result = f"An unexpected error occurred during computation: {str(e)}"

    if problem == "lwe":
        try:
            sigma_e = float(sigma_e_str)
            # Determine the secret key distribution (Xs) based on user selection
            if secret_key_dist_type == 'Binary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseBinary(hw=hamming_weight)
            elif secret_key_dist_type == 'Ternary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseTernary(p=hamming_weight)
            elif secret_key_dist_type == 'DiscreteGaussian':
                # For DiscreteGaussian, sigma_s is required
                sigma_s = float(sigma_s_str)
                Xs = ND.DiscreteGaussian(stddev=sigma_s)
            else:
                # Handle case where an invalid distribution type is received
                raise ValueError("Invalid secret key distribution type selected.")

            # Assuming LWE and ND are defined in the imported 'estimator' module
            myLWE = LWE.Parameters(
                n=n,
                q=q,
                Xs=Xs, # Use the determined secret key distribution
                Xe=ND.DiscreteGaussian(stddev=sigma_e),
            )

            rough = (rough_str.lower() == "true")
            # Assuming LWE.estimate.rough is available and works as expected
            if rough:
                computation_result = LWE.estimate.rough(myLWE, jobs=8)
            else:
                computation_result = LWE.estimate(myLWE, jobs=8)
            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"

        except (ValueError, TypeError) as e:
            # Handle cases where input cannot be converted to the expected type or is invalid (like non-integer q when 'q' type is selected)
            result = f"Error: Invalid input. Please check your values. Details: {str(e)}"
        except Exception as e:
            # Catch any other potential unexpected errors during computation
            result = f"An unexpected error occurred during computation: {str(e)}"
    elif problem == "ntru":
            sigma_e = float(sigma_e_str)
            # Determine the secret key distribution (Xs) based on user selection
            if secret_key_dist_type == 'Binary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseBinary(hw=hamming_weight)
            elif secret_key_dist_type == 'Ternary':
                if hamming_weight_str == "":
                    Xs = ND.UniformMod(2)
                else:
                    hamming_weight = int(hamming_weight_str)
                    Xs = ND.SparseTernary(p=hamming_weight)
            elif secret_key_dist_type == 'DiscreteGaussian':
                # For DiscreteGaussian, sigma_s is required
                sigma_s = float(sigma_s_str)
                Xs = ND.DiscreteGaussian(stddev=sigma_s)
            else:
                # Handle case where an invalid distribution type is received
                raise ValueError("Invalid secret key distribution type selected.")

            # Assuming LWE and ND are defined in the imported 'estimator' module
            myNTRUParams = NTRU.Parameters(
                n=n,
                q=q,
                Xs=Xs, # Use the determined secret key distribution
                Xe=ND.DiscreteGaussian(stddev=sigma_e),
            )

            rough = (rough_str.lower() == "true")
            # Assuming NTRU.estimate.rough is available and works as expected
            if rough:
                computation_result = NTRU.estimate.rough(myNTRUParams, jobs=8)
            else:
                computation_result = NTRU.estimate(myNTRUParams, jobs=8)
            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"
    elif problem == "sis":
            length_bound = float(length_bound_str)
            mySISParams = SIS.Parameters(
                n=n,
                q=q,
                length_bound=length_bound,
            )

            rough = (rough_str.lower() == "true")
            if rough:
                computation_result = SIS.estimate.rough(mySISParams, jobs=8)
            else:
                computation_result = SIS.estimate(mySISParams, jobs=8)
            result = "Each attack provides the following bit security:\n"
            min_security = (None, None)
            for k in computation_result.keys():
                try:
                    bit_security = math.floor(math.log2(computation_result[k]['rop']))
                    result += f"{k} -> {bit_security}-bit security\n"
                    if min_security[1] is None or bit_security < min_security[1]:
                        min_security = (k, bit_security)
                except Exception as e:
                    result += f"{k} -> undefined\n"
            result += "---------------------------------------------\n"
            result += f"Bit-security is at most {min_security[1]}-bits"
    else:
        result = "not implemented"

    # Return the result as a JSON response.
    # jsonify serializes the Python dictionary into a JSON formatted response.
    return jsonify({'result': result})
